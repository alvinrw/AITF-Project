import os
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
            
        # 1. Upload Folder RAW (disimpan ke folder 'raw' di remote repo)
        if os.path.isdir(folder_raw) and os.listdir(folder_raw):
            if notifier: notifier.send("🤗 HuggingFace: Mengunggah folder `raw` ...")
            api.upload_folder(
                folder_path=folder_raw,
                path_in_repo="raw",
                repo_id=repo_id,
                repo_type="dataset"
            )
            
        # 2. Upload CLEAN (File jsonl dimasukkan ke dalam folder 'clean' di remote repo)
        if os.path.exists(clean_file):
            if notifier: notifier.send("🤗 HuggingFace: Mengunggah file `clean` ...")
            api.upload_file(
                path_or_fileobj=clean_file,
                path_in_repo="clean/data_training_cpt.jsonl",
                repo_id=repo_id,
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
