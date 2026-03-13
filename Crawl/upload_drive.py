import os
import io
import zipfile
import json
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import config

# Direktori tempat upload_drive.py berada
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── KONFIGURASI (dari config.py) ───────────────────────────────────
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_FILE       = os.path.join(SCRIPT_DIR, "token.json")
FOLDER_ID        = config.DRIVE_FOLDER_ID
SCOPES           = ["https://www.googleapis.com/auth/drive.file"]

# Prefix nama file di Drive — digunakan untuk identifikasi file lama
DRIVE_FILE_PREFIX = "data_raw_"


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _get_drive_service():
    """
    Authenticate menggunakan akun Google Pribadi (OAuth2), 
    bukan Service Account, agar tidak terkena limit quota 0 bytes.
    """
    creds = None
    # Cek apakah token lama ada
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # Kalau tidak ada kredensial valid (expired/re-auth)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"File kredensial tidak ditemukan: {CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            
            # Agar tidak error saat di-run dari SSH/Server Headless Linux
            try:
                # Coba mode browser (untuk Windows/Mac)
                creds = flow.run_local_server(port=0)
            except Exception:
                # Mode Headless Console (untuk Linux/Server)
                # Script akan nge-print Link Panjang yang harus di klik,
                # lalu setelah dapat kode, user paste kode balasannya kembali ke terminal
                creds = flow.run_local_server(port=8080, open_browser=False)
        
        # Save kredensial buat di run selanjutnya 
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def _zip_folder(folder_path):
    """Compress semua file di folder_path ke BytesIO ZIP."""
    buf        = io.BytesIO()
    file_count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(folder_path)):
            fpath = os.path.join(folder_path, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)
                file_count += 1
    size_kb = buf.tell() // 1024
    buf.seek(0)
    return buf, file_count, size_kb

def _zip_file(file_path):
    """Compress satu file saja ke BytesIO ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_path, os.path.basename(file_path))
    size_kb = buf.tell() // 1024
    buf.seek(0)
    return buf, size_kb

def _count_tokens_simple(file_path):
    """Estimasi token Qwen2.5 sederhana (bytes / 3.7)."""
    if not os.path.exists(file_path): return 0
    size = os.path.getsize(file_path)
    return int(size / 3.7)


def _delete_old_uploads(service):
    """
    Hapus semua file bernama 'data_raw_*' di FOLDER_ID
    agar Drive tidak penuh dengan upload lama.
    Return: jumlah file yang dihapus.
    """
    try:
        query   = f"'{FOLDER_ID}' in parents and name contains '{DRIVE_FILE_PREFIX}' and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives"
        ).execute()
        files   = results.get("files", [])
        for f in files:
            service.files().delete(fileId=f["id"]).execute()
            print(f"[UPLOAD] Dihapus dari Drive: {f['name']} (id={f['id']})")
        return len(files)
    except Exception as e:
        print(f"[UPLOAD] Gagal hapus file lama: {e}")
        return 0


# =============================================================================
# PUBLIC API
# =============================================================================

def upload_data_raw(folder_path="data_raw", clean_file="data_training_cpt.jsonl", notifier=None):
    """
    Zip data_raw dan data_clean, lalu upload keduanya.
    """
    folder_path = os.path.abspath(folder_path)
    clean_path = os.path.abspath(clean_file)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    try:
        service = _get_drive_service()
        _delete_old_uploads(service)
        
        # 1. Upload Raw Markdown (Zipped)
        if os.path.isdir(folder_path) and os.listdir(folder_path):
            zip_buf, file_count, size_kb = _zip_folder(folder_path)
            raw_name = f"data_raw_{timestamp}.zip"
            media = MediaIoBaseUpload(zip_buf, mimetype="application/zip", resumable=True)
            service.files().create(
                body={"name": raw_name, "parents": [FOLDER_ID]},
                media_body=media, fields="id", supportsAllDrives=True
            ).execute()
            if notifier: notifier.send(f"📦 Raw Data Uploaded: {file_count} files ({size_kb} KB)")

        # 2. Upload Clean JSONL (Zipped)
        if os.path.exists(clean_path):
            tokens = _count_tokens_simple(clean_path)
            zip_buf_clean, size_kb_clean = _zip_file(clean_path)
            clean_name = f"data_clean_{timestamp}.zip"
            media_clean = MediaIoBaseUpload(zip_buf_clean, mimetype="application/zip", resumable=True)
            service.files().create(
                body={"name": clean_name, "parents": [FOLDER_ID]},
                media_body=media_clean, fields="id", supportsAllDrives=True
            ).execute()
            
            token_str = f"{tokens / 1_000_000:.2f}M" if tokens > 1_000_000 else f"{tokens / 1_000:.1f}K"
            if notifier: notifier.send(f"✨ Clean Data Uploaded! Token Count: ~{token_str} (Qwen2.5)")

        return True, "Dual Upload Sukses"

    except Exception as e:
        if notifier: notifier.send(f"❌ Upload Gagal: {e}")
        return False, str(e)


# =============================================================================
# STANDALONE
# =============================================================================

if __name__ == "__main__":
    ok, message = upload_data_raw()
    print(message)