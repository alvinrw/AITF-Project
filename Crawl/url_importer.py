import time
import os
from database_manager import DatabaseManager
from duckduckgo_search import DDGS
import config

class URLImporter:
    def __init__(self):
        self.db = DatabaseManager()
        # Engine (binary) berjalan dari root directory sehingga outputnya masuk sini
        self.engine_output = os.path.join("output", "crawler_url.txt")

    def import_from_aitf_engine(self):
        if os.path.exists(self.engine_output):
            print(f"[*] Importing URLs from AITF Engine: {self.engine_output}")
            try:
                with open(self.engine_output, "r", encoding="utf-8") as f:
                    urls = f.readlines()
                
                if urls:
                    count = self.db.add_urls(urls, source="aitf-engine")
                    print(f"[✓] Added {count} new URLs from Engine.")
                
                # WAJIB: Kosongkan file setelah import supaya tidak ada looping
                # pemrosesan ratusan ribu URL yang sama berulang-ulang hingga macet.
                open(self.engine_output, "w").close()
            except Exception as e:
                print(f"[!] Error importing from engine: {e}")

    def import_from_ddgs(self, keywords, max_results=50):
        print(f"[*] Running DDGS fallback for {len(keywords)} keywords...")
        ddgs = DDGS()
        total_added = 0
        for kw in keywords:
            try:
                results = ddgs.text(kw, max_results=max_results)
                urls = [r['href'] for r in results]
                count = self.db.add_urls(urls, source="ddgs")
                total_added += count
                time.sleep(config.SEARCH_DELAY)
            except Exception as e:
                print(f"[!] DDGS Error for '{kw}': {e}")
        print(f"[✓] Added {total_added} new URLs from DDGS.")

if __name__ == "__main__":
    importer = URLImporter()
    
    # Load keywords
    keyword_file = os.path.join(os.path.dirname(__file__), "config", "keyword.txt")
    keywords = []
    if os.path.exists(keyword_file):
        with open(keyword_file, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
    if not keywords:
        print("[!] keyword.txt kosong atau tidak ditemukan. Menggunakan fallback keywords.")
        keywords = ["kemiskinan", "bantuan sosial", "BLT jawa timur"]

    print(f"[*] URL Importer started. Menggunakan DDGS sebagai Producer utama ({len(keywords)} keywords).")
    
    import random
    
    while True:
        try:
            # Tetap cek AITF Engine jika suatu saat jalan
            importer.import_from_aitf_engine()
            
            # Acak urutan keyword dan ambil 40 sampel per siklus
            random.shuffle(keywords)
            subset_keywords = keywords[:40]
            
            # Tambahkan variasi pencarian agar hasil DDGS tidak identik setiap saat
            variations = ["", " site:go.id", " site:ac.id", " site:id", " filetype:pdf", " jurnal", " 2024", " jatim"]
            active_keywords = [kw + random.choice(variations) for kw in subset_keywords]
            
            # Jalankan DDGS
            importer.import_from_ddgs(active_keywords, max_results=25) 
            
            # Tunggu agak lama sebelum nge-cycle keywords yang sama
            print("[*] Sesi DDGS selesai. Tidur selama 2 menit...")
            time.sleep(120) 
        except Exception as e:
            print(f"[!] Importer Loop Error: {e}")
            time.sleep(60)
