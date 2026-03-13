import time
import os
from database_manager import DatabaseManager
from duckduckgo_search import DDGS
import config

class URLImporter:
    def __init__(self):
        self.db = DatabaseManager()
        self.engine_output = os.path.join("crawler-engine", "Windows", "output", "crawler_url.txt")
        # Sesuaikan jika di Linux
        if not os.path.exists(self.engine_output):
            self.engine_output = os.path.join("crawler-engine", "Linux", "output", "crawler_url.txt")

    def import_from_aitf_engine(self):
        if os.path.exists(self.engine_output):
            print(f"[*] Importing URLs from AITF Engine: {self.engine_output}")
            try:
                with open(self.engine_output, "r", encoding="utf-8") as f:
                    urls = f.readlines()
                count = self.db.add_urls(urls, source="aitf-engine")
                print(f"[✓] Added {count} new URLs from Engine.")
                # Opsional: Kosongkan file setelah import agar tidak berat
                # open(self.engine_output, "w").close()
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
    # Contoh manual run
    # importer.import_from_aitf_engine()
    # importer.import_from_ddgs(["kemiskinan jawa timur", "bansos jatim"])
