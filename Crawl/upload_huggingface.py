import os
import shutil
import tempfile
from huggingface_hub import HfApi
import config

# HuggingFace membatasi 10.000 file per direktori.
# Solusi: bagi file raw ke subdirektori berdasarkan 2 karakter pertama nama file.
# Contoh: "bps.go.id_abc.md" → raw/bp/bps.go.id_abc.md
# Ini memberi hingga ~256 bucket, masing-masing menampung ribuan file.

def _get_bucket(filename):
    """Kembalikan nama subdirektori (2 char pertama nama file, lowercase)."""
    prefix = filename[:2].lower()
    # Pastikan prefix hanya mengandung karakter aman untuk path
    safe = ''.join(c if c.isalnum() else '_' for c in prefix)
    return safe if safe else '__'

def upload_to_huggingface(repo_id="alvinrifky/Crawling-MKN_1", folder_raw="data_raw", clean_file="data/data_training_cpt.jsonl", notifier=None):
    try:
        token = getattr(config, 'HF_TOKEN', None)
        api = HfApi(token=token)
        
        # Buat repo dataset kalau belum ada
        try:
            api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        except Exception as repo_e:
            print(f"[HfApi] Peringatan create_repo: {repo_e}")
        
        # ── UPLOAD RAW DATA (dibagi ke subdirektori agar tidak melebihi 10k per dir) ──
        if os.path.isdir(folder_raw):
            if notifier: notifier.send("🤗 HuggingFace: Menyiapkan upload folder raw/ (dibagi ke sub-bucket)...")
            print(f"[HF] Menyiapkan shadow folder dengan struktur bucket...")

            with tempfile.TemporaryDirectory() as tmp_raw:
                target_root = os.path.join(tmp_raw, "raw")
                os.makedirs(target_root)

                files_copied = 0
                bucket_counts = {}

                for item in os.listdir(folder_raw):
                    if item.endswith(".zip"):
                        continue  # Lewati backup zip
                    s = os.path.join(folder_raw, item)
                    if not os.path.isfile(s):
                        continue

                    bucket = _get_bucket(item)
                    bucket_dir = os.path.join(target_root, bucket)
                    os.makedirs(bucket_dir, exist_ok=True)
                    shutil.copy2(s, os.path.join(bucket_dir, item))
                    files_copied += 1
                    bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

                print(f"[HF] {files_copied} file disiapkan ke {len(bucket_counts)} bucket.")
                print(f"[HF] Distribusi bucket: { {k: v for k, v in sorted(bucket_counts.items())} }")
                print(f"[HF] Memulai upload raw/...")

                api.upload_large_folder(
                    repo_id=repo_id,
                    folder_path=tmp_raw,
                    repo_type="dataset",
                )
                print(f"[HF] Upload raw/ selesai.")

        # ── UPLOAD CLEAN DATA ──────────────────────────────────────────────────
        if os.path.exists(clean_file):
            if notifier: notifier.send("🤗 HuggingFace: Mengupload file clean/...")
            print(f"[HF] Upload clean/{os.path.basename(clean_file)}...")
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
