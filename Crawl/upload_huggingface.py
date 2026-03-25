import os
import shutil
import tempfile
from huggingface_hub import HfApi
import config

def upload_to_huggingface(repo_id="alvinrifky/Crawling-MKN_1", folder_raw="data_raw", clean_file="data/data_training_cpt.jsonl", notifier=None):
    try:
        # Gunakan token dari config jika disetel
        token = getattr(config, 'HF_TOKEN', None)
        api = HfApi(token=token)
        
        # Buat repo dataset kalau belum ada
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        except Exception as repo_e:
            print(f"[HfApi] Peringatan create_repo: {repo_e}")
            
        # STRATEGI: Shadow Folder
        # Karena upload_large_folder tidak mendukung path_in_repo, kita buat struktur lokal 
        # yang sama persis dengan yang diinginkan di remote repo, lalu upload foldernya.
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            if notifier: notifier.send("🤗 HuggingFace: Menyiapkan struktur folder (Shadow Folder)...")
            
            # 1. Siapkan folder raw/
            target_raw = os.path.join(tmp_dir, "raw")
            os.makedirs(target_raw)
            if os.path.isdir(folder_raw):
                for item in os.listdir(folder_raw):
                    if item.endswith(".zip"): continue # Lewati backup zip
                    s = os.path.join(folder_raw, item)
                    d = os.path.join(target_raw, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d) # Copy file ke shadow folder
            
            # 2. Siapkan folder clean/
            target_clean = os.path.join(tmp_dir, "clean")
            os.makedirs(target_clean)
            if os.path.exists(clean_file):
                shutil.copy2(clean_file, os.path.join(target_clean, os.path.basename(clean_file)))

            # 3. Upload menggunakan upload_large_folder
            if notifier: notifier.send("🤗 HuggingFace: Memulai proses sinkronisasi (upload_large_folder)...")
            
            api.upload_large_folder(
                repo_id=repo_id,
                folder_path=tmp_dir,
                repo_type="dataset"
            )
            
        if notifier: notifier.send(f"✅ HuggingFace Upload Sukses!\nDataset ada di: huggingface.co/datasets/{repo_id}")
        return True, "Upload HuggingFace Sukses"
        
    except Exception as e:
        if notifier: notifier.send(f"❌ Upload HuggingFace Gagal: {e}")
        return False, str(e)

if __name__ == "__main__":
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_to_huggingface(
        clean_file=os.path.join(_base_dir, "data", "data_training_cpt.jsonl"),
        folder_raw=os.path.join(_base_dir, "data_raw")
    )
