import os
import json
import hashlib
import re
try:
    from transformers import AutoTokenizer
except ImportError:
    print("Harap install transformers terlebih dahulu: pip install transformers")
    exit()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "data", "markdown")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "dataset.jsonl")
MODEL_NAME = "Qwen/Qwen3-8B"  # Ubah ke versi Qwen yang Anda gunakan (contoh: Qwen/Qwen2.5-7B atau lainnya)

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Folder '{INPUT_DIR}' tidak ditemukan!")
        return

    print(f"Memuat Tokenizer dari {MODEL_NAME}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    except Exception as e:
        print(f"Gagal memuat tokenizer: {e}")
        return

    total_tokens = 0
    total_files = 0
    total_duplicates = 0
    seen_hashes = set()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for filename in os.listdir(INPUT_DIR):
            if filename.endswith(".md"):
                file_path = os.path.join(INPUT_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f_in:
                        content = f_in.read()

                    if not content.strip():
                        continue

                    # Normalisasi teks (hapus spasi ekstra dan ubah ke lowercase) untuk perbandingan
                    normalized_text = re.sub(r'\s+', ' ', content).strip().lower()
                    content_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()

                    # Cek apakah isi konten ini sudah pernah diproses sebelumnya
                    if content_hash in seen_hashes:
                        print(f"[SKIP] Konten duplikat terdeteksi pada: {filename}")
                        total_duplicates += 1
                        continue
                    
                    seen_hashes.add(content_hash)

                    # Menghitung token
                    tokens = tokenizer.encode(content)
                    token_count = len(tokens)
                    total_tokens += token_count
                    total_files += 1

                    # Menyimpan ke format JSONL
                    # Format dasar untuk pretraining/SFT (Instruction Tuning) bisa disesuaikan lagi.
                    json_record = {
                        "text": content,
                        "source": filename,
                        "tokens": token_count
                    }
                    f_out.write(json.dumps(json_record, ensure_ascii=False) + '\n')

                except Exception as e:
                    print(f"Error saat membaca file {filename}: {e}")

    print("="*40)
    print(f"Proses Selesai!")
    print(f"Total file diproses: {total_files}")
    print(f"Total file duplikat (diabaikan): {total_duplicates}")
    print(f"Total token (menggunakan {MODEL_NAME}): {total_tokens:,}")
    print(f"Dataset berhasil disimpan di: {OUTPUT_FILE}")
    print("="*40)

if __name__ == "__main__":
    main()
