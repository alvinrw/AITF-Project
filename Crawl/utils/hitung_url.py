import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data_raw")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "visited_urls.txt")

def recover_urls():
    if not os.path.exists(DATA_DIR):
        print(f"[!] Folder {DATA_DIR} tidak ditemukan. Pastikan data .md atau .json sudah diekstrak.")
        return

    found_urls = set()
    files = os.listdir(DATA_DIR)
    
    print(f"[*] Mencari URL dari {len(files)} file di dalam {DATA_DIR}...")
    
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        if filename.endswith(".md"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("url:"):
                            url = line.replace("url:", "").strip()
                            if url:
                                found_urls.add(url)
                            break # Hanya cari satu baris url di atas
            except Exception as e:
                pass
        # Jika JSON juga menyimpan URL, tambahkan percabangan disini
    
    if found_urls:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for url in sorted(found_urls):
                f.write(url + '\n')
        print(f"[SUCCESS] Berhasil memulihkan {len(found_urls)} URL dan disimpan di {OUTPUT_FILE}!")
    else:
        print("[!] Tidak ada URL yang ditemukan dari file hasil crawl.")

if __name__ == "__main__":
    recover_urls()