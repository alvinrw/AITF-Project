import os
import zipfile
import tempfile
from huggingface_hub import HfApi
import config

def upload_to_huggingface(repo_id="alvinrifky/Crawling-MKN_1", folder_raw="data_raw", clean_file="data/data_training_mixed.jsonl", wikipedia_file="data/wikipedia_subset.jsonl", notifier=None):
    try:
        token = getattr(config, 'HF_TOKEN', None)
        api = HfApi(token=token)
        
        # Buat repo dataset kalau belum ada
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        except Exception as repo_e:
            print(f"[HfApi] Peringatan create_repo: {repo_e}")

        with tempfile.TemporaryDirectory() as tmp_dir:

            # ── 1. UPLOAD RAW CRAWLING (Zipped) ───────────────────────────────
            if os.path.isdir(folder_raw):
                zip_path = os.path.join(tmp_dir, "raw.zip")
                if notifier: notifier.send("🤗 HuggingFace: Mengemas data crawling ke zip...")
                print(f"[HF] Mengemas {folder_raw}/ → raw.zip ...")

                file_count = 0
                with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                    for item in sorted(os.listdir(folder_raw)):
                        if item.endswith(".zip"): continue
                        s = os.path.join(folder_raw, item)
                        if os.path.isfile(s):
                            zf.write(s, arcname=item)
                            file_count += 1

                print(f"[HF] ✅ raw.zip siap. Uploading ke 'dataraw_crawling/raw.zip'...")
                api.upload_file(
                    path_or_fileobj=zip_path,
                    path_in_repo="dataraw_crawling/raw.zip",
                    repo_id=repo_id,
                    repo_type="dataset",
                )

            # ── 2. UPLOAD WIKIPEDIA SUBSET ────────────────────────────────────
            if os.path.exists(wikipedia_file):
                if notifier: notifier.send("🤗 HuggingFace: Mengupload Wikipedia subset...")
                print(f"[HF] Uploading {wikipedia_file} ke 'data_wikiped/'...")
                api.upload_file(
                    path_or_fileobj=wikipedia_file,
                    path_in_repo=f"data_wikiped/{os.path.basename(wikipedia_file)}",
                    repo_id=repo_id,
                    repo_type="dataset",
                )

            # ── 3. UPLOAD CLEAN MIXED DATA ────────────────────────────────────
            if os.path.exists(clean_file):
                if notifier: notifier.send("🤗 HuggingFace: Mengupload file clean gabungan...")
                print(f"[HF] Uploading {clean_file} ke 'clean/'...")
                api.upload_file(
                    path_or_fileobj=clean_file,
                    path_in_repo=f"clean/{os.path.basename(clean_file)}",
                    repo_id=repo_id,
                    repo_type="dataset",
                )
            else:
                print(f"[HF] File clean tidak ditemukan, dilewati: {clean_file}")

        if notifier: notifier.send(f"✅ HuggingFace Upload Sukses!\nDataset: huggingface.co/datasets/{repo_id}")
        print(f"[HF] ✅ Semua upload selesai!")
        return True, "Upload HuggingFace Sukses"
        
    except Exception as e:
        if notifier: notifier.send(f"❌ Upload HuggingFace Gagal: {e}")
        print(f"[HF] ❌ Error: {e}")
        return False, str(e)

if __name__ == "__main__":
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_to_huggingface(
        clean_file=os.path.join(_base_dir, "data", "data_training_mixed.jsonl"),
        folder_raw=os.path.join(_base_dir, "data_raw")
    )
