"""
upload_drive.py — Module upload data_raw ke Google Drive.

Cara pakai:
  from upload_drive import upload_data_raw
  ok, msg = upload_data_raw()

Atau jalankan standalone:
  python upload_drive.py
"""

import os
import io
import zipfile
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import config

# Direktori tempat upload_drive.py berada
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── KONFIGURASI (dari config.py) ───────────────────────────────────
SERVICE_ACCOUNT_FILE = os.path.join(SCRIPT_DIR, config.SERVICE_ACCOUNT_FILE)
FOLDER_ID            = config.DRIVE_FOLDER_ID
SCOPES               = ["https://www.googleapis.com/auth/drive.file"]

# Prefix nama file di Drive — digunakan untuk identifikasi file lama
DRIVE_FILE_PREFIX = "data_raw_"


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _get_drive_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


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


def _delete_old_uploads(service):
    """
    Hapus semua file bernama 'data_raw_*' di FOLDER_ID
    agar Drive tidak penuh dengan upload lama.
    Return: jumlah file yang dihapus.
    """
    try:
        query   = f"'{FOLDER_ID}' in parents and name contains '{DRIVE_FILE_PREFIX}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
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

def upload_data_raw(folder_path="data_raw", notifier=None):
    """
    Zip seluruh isi folder_path, hapus upload lama di Drive,
    lalu upload zip baru.

    Returns
    -------
    (success: bool, message: str)
    """
    folder_path = os.path.abspath(folder_path)

    if not os.path.isdir(folder_path):
        msg = f"❌ Folder tidak ditemukan: {folder_path}"
        if notifier: notifier.send(msg)
        return False, msg

    files_in_folder = [f for f in os.listdir(folder_path)
                       if os.path.isfile(os.path.join(folder_path, f))]
    if not files_in_folder:
        msg = "⚠️ Folder data_raw kosong, tidak ada yang di-upload."
        if notifier: notifier.send(msg)
        return False, msg

    try:
        if notifier:
            notifier.send(
                f"⬆️ <b>Upload ke Drive dimulai…</b>\n"
                f"Mem-zip {len(files_in_folder)} file di <code>data_raw/</code>"
            )

        # 1. Zip folder
        zip_buf, file_count, size_kb = _zip_folder(folder_path)

        # 2. Koneksi ke Drive
        service = _get_drive_service()

        # 3. Hapus upload lama (data_raw_*.zip) di folder yang sama
        deleted = _delete_old_uploads(service)
        if deleted > 0 and notifier:
            notifier.send(f"🗑️ {deleted} file upload lama dihapus dari Drive.")

        # 4. Upload zip baru
        timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M")
        drive_name = f"{DRIVE_FILE_PREFIX}{timestamp}.zip"

        media  = MediaIoBaseUpload(zip_buf, mimetype="application/zip", resumable=True)
        result = service.files().create(
            body={"name": drive_name, "parents": [FOLDER_ID]},
            media_body=media,
            fields="id, name",
        ).execute()

        drive_file_id = result.get("id", "-")
        msg = (
            f"✅ <b>Upload berhasil!</b>\n"
            f"📦 <code>{drive_name}</code>\n"
            f"📁 {file_count} file | {size_kb:,} KB\n"
            f"🆔 Drive ID: <code>{drive_file_id}</code>"
        )
        if notifier: notifier.send(msg)
        print(f"[UPLOAD] Berhasil: {drive_name} ({file_count} file, {size_kb} KB)")
        return True, msg

    except Exception as e:
        msg = f"❌ Upload gagal: {e}"
        if notifier: notifier.send(msg)
        print(f"[UPLOAD] {msg}")
        return False, msg


# =============================================================================
# STANDALONE
# =============================================================================

if __name__ == "__main__":
    ok, message = upload_data_raw()
    print(message)