import os
import shutil
import tempfile
from huggingface_hub import HfApi
import config

def upload_to_huggingface(repo_id="alvinrifky/Crawling-MKN_1", folder_raw="data_raw", clean_file="data/data_training_cpt.jsonl", notifier=None):
    try:
        token = getattr(config, 'HF_TOKEN', None)
        api = HfApi(token=token)
        
        # Buat repo dataset kalau belum ada
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        except Exception as repo_e:
            print(f"[HfApi] Peringatan create_repo: {repo_e}")
        
        # ── UPLOAD RAW DATA ────────────────────────────────────────────────────
        # Gunakan tempdir sebagai shadow folder untuk raw/ agar struktur folder di
        # HuggingFace tetap rapi tanpa harus copy semua file sekaligus.
        if os.path.isdir(folder_raw):
            if notifier: notifier.send("🤗 HuggingFace: Menyiapkan upload folder raw/...")
            print(f"[HF] Menyiapkan shadow folder untuk raw/...")
            
            with tempfile.TemporaryDirectory() as tmp_raw:
                # Buat struktur raw/ di dalam tempdir
                target_raw = os.path.join(tmp_raw, "raw")
                os.makedirs(target_raw)
                
                files_copied = 0
                for item in os.listdir(folder_raw):
                    if item.endswith(".zip"):
                        continue  # Lewati backup zip
                    s = os.path.join(folder_raw, item)
                    d = os.path.join(target_raw, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                        files_copied += 1
                
                print(f"[HF] {files_copied} file disiapkan. Memulai upload raw/...")
                api.upload_large_folder(
                    repo_id=repo_id,
                    folder_path=tmp_raw,
                    repo_type="dataset",
                )
                print(f"[HF] Upload raw/ selesai.")

        # ── UPLOAD CLEAN DATA ──────────────────────────────────────────────────
        if os.path.exists(clean_file):
            if notifier: notifier.send("🤗 HuggingFace: Mengupload file clean/...")
            print(f"[HF] Memulai upload clean/{os.path.basename(clean_file)}...")
            
            api.upload_file(
                path_or_fileobj=clean_file,
                path_in_repo=f"clean/{os.path.basename(clean_file)}",
                repo_id=repo_id,
                repo_type="dataset",
            )
            print(f"[HF] Upload clean/ selesai.")
        else:
            print(f"[HF] File clean tidak ditemukan, dilewati: {clean_file}")

        if notifier: notifier.send(f"✅ HuggingFace Upload Sukses!\nDataset ada di: huggingface.co/datasets/{repo_id}")
        print(f"[HF] ✅ Semua upload selesai!")
        return True, "Upload HuggingFace Sukses"
        
    except Exception as e:
        if notifier: notifier.send(f"❌ Upload HuggingFace Gagal: {e}")
        print(f"[HF] ❌ Error: {e}")
        return False, str(e)

if __name__ == "__main__":
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_to_huggingface(
        clean_file=os.path.join(_base_dir, "data", "data_training_cpt.jsonl"),
        folder_raw=os.path.join(_base_dir, "data_raw")
    )
