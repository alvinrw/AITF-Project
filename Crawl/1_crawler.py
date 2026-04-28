import os
import time
from duckduckgo_search import DDGS

KEYWORD_FILE = os.path.join("config", "web_Keyword.txt")
OUTPUT_FILE = "output.txt"
STATE_FILE = "crawler_state.txt"

def load_processed_lines():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.isdigit():
                return int(content)
    return 0

def save_processed_lines(line_number):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(line_number))

def load_existing_urls():
    existing_urls = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                existing_urls.add(line.strip())
    return existing_urls

def append_url(url):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def main():
    if not os.path.exists(KEYWORD_FILE):
        print(f"[!] File keyword tidak ditemukan: {KEYWORD_FILE}")
        return

    with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    total_keywords = len(keywords)
    start_idx = load_processed_lines()
    existing_urls = load_existing_urls()
    
    print(f"[*] Total Keywords: {total_keywords}")
    if start_idx > 0:
        print(f"[*] Melanjutkan dari baris ke-{start_idx + 1}")
    
    ddgs = DDGS()
    
    for i in range(start_idx, total_keywords):
        keyword = keywords[i]
        print(f"[{i+1}/{total_keywords}] Mencari: {keyword}")
        
        try:
            # Menggunakan ddgs.text untuk mencari
            results = ddgs.text(keyword, max_results=10)
            
            new_url_count = 0
            if results:
                for result in results:
                    url = result.get('href')
                    if url and url not in existing_urls:
                        existing_urls.add(url)
                        append_url(url)
                        new_url_count += 1
            
            print(f"    -> Ditemukan {new_url_count} URL baru.")
            
        except Exception as e:
            print(f"[!] Error saat mencari '{keyword}': {e}")
            print("[!] Hentikan sementara (rate limit/error), menyimpan progress...")
            break # Berhenti agar bisa di-resume nanti
            
        # Simpan progress setiap berhasil 1 keyword
        save_processed_lines(i + 1)
        
        # Delay agar tidak kena blokir (Rate limit DDGS cukup ketat)
        time.sleep(2)

    print("[*] Proses crawling selesai atau dihentikan sementara.")

if __name__ == "__main__":
    main()
