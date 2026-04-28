import os
import io
import zipfile
import sys
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# ── ADJUST PATH UNTUK MENGAMBIL CONFIG DARI FOLDER CRAWL ──
# Script ini ada di Training/Core, folder Crawl ada di level atasnya
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
AITF_DIR    = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
CRAWL_DIR   = os.path.join(AITF_DIR, "Crawl")

# Masukkan folder Crawl ke sys.path agar bisa import config.py
sys.path.append(CRAWL_DIR)
import config

# ── KONFIGURASI ────────────────────────────────────────────────
# Path directory home
_HOME = os.path.expanduser('~')

# Arahkan path credentials ke folder Testing
CREDENTIALS_FILE = os.path.join(_HOME, 'Testing', 'credentials.json')
TOKEN_FILE       = os.path.join(_HOME, 'Testing', 'token.json')
PARENT_FOLDER_ID = config.DRIVE_FOLDER_ID  # Folder utama AITF Crawler di Drive
SCOPES           = ["https://www.googleapis.com/auth/drive.file"]

# Path model di server
if len(sys.argv) > 1:
    MODEL_DIR = sys.argv[1]
else:
    MODEL_DIR = os.path.expanduser("~/Testing_0_5B/output/qwen2_5_0_5b_cpt/merged-model")
# ===============================================================

def _get_drive_service():
    """Authenticate pakai Google OAuth2."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"File kredensial tidak ditemukan: {CREDENTIALS_FILE} \nPastikan kamu menjalankan ini di mana folder credentials berada.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            try:
                creds = flow.run_local_server(port=0)
            except Exception:
                creds = flow.run_local_server(port=8080, open_browser=False)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def _get_or_create_subfolder(service, folder_name, parent_id):
    """Cari folder dengan nama tertentu di dalam parent_id, kalau ga ada ya buat baru."""
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if len(files) > 0:
        return files[0]['id']
    else:
        # Buat folder baru
        folder_metadata = {
            'name': folder_name,
            'parents': [parent_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        print(f"📁 Folder '{folder_name}' berhasil dibuat di Drive.")
        return folder.get('id')

def _zip_folder_large(folder_path):
    """
    Simpan zip besar ke temporary file, BUKAN di memory (BytesIO) 
    biar nggak bikin RAM meledak (model weights kan gede bisa GB).
    """
    zip_path = os.path.join(os.path.dirname(folder_path), "temp_model_upload.zip")
    file_count = 0
    print(f"📦 Zipping {folder_path} to {zip_path} ... (ini butuh waktu krn file besar)")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Jalan ke semua folder & subfolder
        for root, _, files in os.walk(folder_path):
            for file in files:
                fpath = os.path.join(root, file)
                arcname = os.path.relpath(fpath, folder_path)
                zf.write(fpath, arcname)
                file_count += 1
                
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    return zip_path, file_count, size_mb

def main():
    if not os.path.exists(MODEL_DIR):
        print(f"❌ Error: Folder model {MODEL_DIR} tidak ditemukan!")
        sys.exit(1)
        
    print(f"🚀 Mulai Upload Model ({MODEL_DIR}) ke Google Drive...")
    
    try:
        service = _get_drive_service()
        
        # 1. Bikin/cari folder "CPT Model 0.5B"
        model_folder_id = _get_or_create_subfolder(service, "CPT Model 0.5B", PARENT_FOLDER_ID)
        
        # 2. Nge-zip folder model di server
        zip_path, file_count, size_mb = _zip_folder_large(MODEL_DIR)
        print(f"✅ Zip selesai! Terdiri dari {file_count} files, Total size: {size_mb:.2f} MB")
        
        # 3. Upload file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        zip_name = f"Qwen2.5-0.5B-AITF-CPT_{timestamp}.zip"
        
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(zip_path, mimetype="application/zip", resumable=True)
        
        print(f"☁️ Uploading {zip_name} to Google Drive... (Tunggu ya)")
        request = service.files().create(
            body={"name": zip_name, "parents": [model_folder_id]},
            media_body=media, fields="id", supportsAllDrives=True
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   Upload progress: {int(status.progress() * 100)}%")
                
        print(f"✅ UPLOAD SUKSES! File ID: {response.get('id')}")
        
        # Cleanup
        os.remove(zip_path)
        print("🧹 File zip sementara sudah dihapus.")
        
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")

if __name__ == "__main__":
    main()
