import os
import sys
from huggingface_hub import HfApi, login

# ── ADJUST PATH UNTUK MENGAMBIL CONFIG DARI FOLDER CRAWL ──
# Script ini ada di Training/Core, folder Crawl ada di level atasnya
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
AITF_DIR    = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
CRAWL_DIR   = os.path.join(AITF_DIR, "Crawl")

sys.path.append(CRAWL_DIR)
try:
    import config
except ImportError:
    print("❌ Error: Tidak dapat mengimport module config dari folder Crawl.")
    sys.exit(1)

# ===============================================================
# KONFIGURASI HUGGING FACE
# ===============================================================
# 1. Ganti dengan repo tujuan kamu di Hugging Face
# Format: "username_kamu/nama_model" (Contoh: "alvinrw/Qwen2.5-0.5B-AITF-CPT")
REPO_ID = "alvinrifky/Qwen2.5-0.5B-AITF-CPT"

# 2. Ambil token dari config.py di folder Crawl
HF_TOKEN = getattr(config, 'HF_TOKEN', None)

# 3. Path directory model hasil training (Pilih folder model yang mau di upload)
# Biasanya model yang di upload adalah model yang SUDAH di-merge agar bisa
# langsung dipanggil menggunakan 'from_pretrained("username/model")'
MODEL_DIR = os.path.expanduser("~/Testing_0_5B/output/qwen2_5_0_5b_cpt/merged-model")
# ===============================================================

def main():
    if not os.path.exists(MODEL_DIR):
        print(f"❌ Error: Folder model {MODEL_DIR} tidak ditemukan!")
        print("Pastikan pipeline training sudah berhasil sampai tahap merge model.")
        sys.exit(1)
        
    if not HF_TOKEN or HF_TOKEN.startswith("hf_***"):
        print("❌ Error: Harap masukkan HF_TOKEN kamu yang valid di config.py (Folder Crawl).")
        sys.exit(1)

    print(f"🚀 Mulai Login ke Hugging Face...")
    try:
        # Melakukan login dengan token
        login(token=HF_TOKEN, add_to_git_credential=True)
        print("✅ Login Berhasil!")
    except Exception as e:
        print(f"❌ Gagal login: {e}")
        sys.exit(1)

    print(f"\n📦 Bersiap mengupload folder {MODEL_DIR} ...")
    print(f"☁️ Target Repository: https://huggingface.co/{REPO_ID}")
    
    api = HfApi()

    # Membuat repository jika belum ada
    try:
        api.create_repo(repo_id=REPO_ID, repo_type="model", exist_ok=True, private=False)
        print(f"✅ Repository {REPO_ID} tersedia.")
    except Exception as e:
        print(f"⚠️ Peringatan saat memastikan/membuat repository: {e}")
    
    # Upload seluruh isi folder
    print("⏳ Sedang mengupload model (ini mungkin membutuhkan waktu bergantung dari koneksi dan ukuran file)...")
    try:
        api.upload_folder(
            folder_path=MODEL_DIR,
            repo_id=REPO_ID,
            repo_type="model",
            commit_message="Upload CPT merged model"
        )
        print("🎉 UPLOAD SUKSES!")
        print(f"Kini kamu bisa memanggil model ini dengan cara:")
        print(f'>>> model = AutoModelForCausalLM.from_pretrained("{REPO_ID}")')
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat upload: {e}")

if __name__ == "__main__":
    main()
