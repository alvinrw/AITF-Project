from huggingface_hub import HfApi, create_repo, upload_folder
import os

# ===== CONFIG =====
HF_TOKEN = "YOUR_HF_TOKEN_HERE"  # Masukkan token Hugging Face Anda
USERNAME = "alvinrifky"
REPO_NAME = "Qwen3-8B-AITF-CPT-V2"

LOCAL_PATH = "/home/jovyan/MKN-1/Training_cpt_qwen8B_v2/output/qwen3_cpt_8b_v2_final"

# ==================

repo_id = f"{USERNAME}/{REPO_NAME}"

# Init API
api = HfApi(token=HF_TOKEN)

# 1. Buat repo (kalau belum ada)
try:
    create_repo(
        repo_id=repo_id,
        repo_type="model",
        exist_ok=True,
        token=HF_TOKEN
    )
    print(f"✅ Repo siap: {repo_id}")
except Exception as e:
    print(f"⚠️ Repo mungkin sudah ada: {e}")

# 2. Upload folder
print("🚀 Uploading model...")
upload_folder(
    repo_id=repo_id,
    folder_path=LOCAL_PATH,
    path_in_repo="",
    repo_type="model",
    token=HF_TOKEN
)

print("🎉 Upload selesai!")
print(f"👉 https://huggingface.co/{repo_id}")