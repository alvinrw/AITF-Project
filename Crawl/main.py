import os
import io
import requests
import json
import time
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from datetime import datetime
from duckduckgo_search import DDGS
from bot_monitor import TelegramNotifier
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("[!] pdfplumber tidak ditemukan. Jalankan: pip install pdfplumber")

class WebCrawlerAI:
    def __init__(self, output_dir="data_raw", blocked_file="blocked_domain.txt", priority_file="domain_priority.txt", keyword_file="keyword.txt", notifier=None, visited_file="visited_urls.txt"):
        self.output_dir = output_dir
        self.visited_file = visited_file
        self.visited_urls = self._load_visited()
        self.content_hashes = set() # Untuk cegah data duplikat konten
        self.blocked_domains = self._load_list(blocked_file)
        self.priority_domains = self._load_list(priority_file)
        self.search_keywords = self._load_list(keyword_file)
        self.notifier = notifier
        
        # --- FILTER RELEVANSI KETAT ---
        # Wajib ada minimal satu dari CORE (Inti Masalah)
        self.core_keywords = [
            # Kemiskinan
            'miskin', 'kemiskinan', 'poverty',
            # BLT & Bansos
            'blt', 'bansos', 'bantuan langsung tunai', 'penerima bantuan',
            # Program Sosial
            'pkh', 'dtks', 'desil', 'kip', 'bpnt', 
            # Rentan Sosial
            'rentan', 'marjinal', 'subsidi', 'graduasi',
        ]
        # Wajib ada minimal satu dari CONTEXT (Lokasi/Sumber/Konteks)
        self.context_keywords = [
            # Umum Jatim
            'jatim', 'jawa timur',
            # Instansi/Program
            'bps', 'sosial', 'bansos', 'bantuan', 'dana desa', 'puspa', 'pkh', 'dtks',
            # 38 Kabupaten/Kota Jawa Timur
            'surabaya', 'malang', 'kediri', 'blitar', 'mojokerto', 'madiun', 'probolinggo', 'pasuruan',
            'batu', 'madura', 'bangkalan', 'sampang', 'pamekasan', 'sumenep',
            'sidoarjo', 'gresik', 'lamongan', 'tuban', 'bojonegoro',
            'jombang', 'nganjuk', 'magetan', 'ngawi', 'ponorogo', 'pacitan', 'trenggalek', 'tulungagung',
            'blitar', 'kediri', 'jember', 'banyuwangi', 'situbondo', 'bondowoso',
            'lumajang', 'probolinggo', 'pasuruan', 'malang',
            # Wilayah Khusus
            'tapal kuda', 'mataraman', 'arek', 'pantura', 'madura',
        ]
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"[*] Folder output created: {self.output_dir}")

    def _load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return []

    def _load_visited(self):
        """Load visited URLs dari file agar tidak crawl ulang antar run."""
        if os.path.exists(self.visited_file):
            with open(self.visited_file, 'r', encoding='utf-8') as f:
                urls = {line.strip() for line in f if line.strip()}
            print(f"[*] Loaded {len(urls)} visited URLs dari {self.visited_file}")
            return urls
        return set()

    def _save_visited(self, url):
        """Append satu URL baru ke file visited secara incremental."""
        with open(self.visited_file, 'a', encoding='utf-8') as f:
            f.write(url + '\n')

    def _get_hash(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def get_source_type(self, url):
        """Kategorisasi otomatis berdasarkan pola domain."""
        domain = urlparse(url).netloc.lower()
        # Pemerintah: go.id, lembaga resmi
        if any(x in domain for x in ['go.id', 'tnp2k', 'bappeda', 'dinsos', 'kemensos', 'bps']):
            return 'government'
        # Akademik: ac.id, journal, ejournal, repository
        if any(x in domain for x in ['ac.id', 'journal', 'ejournal', 'repository', 'jurnal']):
            return 'academic'
        # Berita & Lainnya
        return 'news'

    def get_quality_score(self, text, url):
        """Skoring kualitas 0-100 untuk auto-curation."""
        score = 0
        text_lower = text.lower()
        # Panjang teks (max 40 poin)
        score += min(40, len(text) // 100)
        # Kepadatan keyword core (max 30 poin)
        core_hits = sum(text_lower.count(ck) for ck in self.core_keywords)
        score += min(30, core_hits * 3)
        # Bonus domain terpercaya (30 poin)
        if self.get_source_type(url) == 'government':
            score += 30
        elif self.get_source_type(url) == 'academic':
            score += 25
        else:
            score += 10
        return min(100, score)

    def _extract_pdf_text(self, response_content):
        """Ekstrak teks dari bytes PDF menggunakan pdfplumber."""
        if not PDF_SUPPORT:
            return None
        try:
            with pdfplumber.open(io.BytesIO(response_content)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text.strip())
            return " ".join(pages_text)
        except Exception as e:
            print(f"[!] PDF parse error: {e}")
            return None

    def is_indonesian_domain(self, url):
        """Pastikan domain berakhiran .id ATAU ada di daftar prioritas (misal: kompas.com)."""
        domain = urlparse(url).netloc.lower()
        # Izinkan domain Indonesia (.id TLD)
        if domain.endswith('.id'):
            return True
        # Izinkan domain yang ada di daftar prioritas (walau bukan .id)
        for priority in self.priority_domains:
            if priority.lower() in domain:
                return True
        return False

    def is_blocked(self, url):
        domain = urlparse(url).netloc.lower()
        # Blokir otomatis domain pencari bot dan sampah umum
        if any(x in domain for x in ['google.com', 'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com']):
            return True
        for blocked in self.blocked_domains:
            if blocked.lower() in domain:
                return True
        # Blokir domain non-Indonesia yang tidak ada di daftar prioritas
        if not self.is_indonesian_domain(url):
            return True
        return False

    def is_priority(self, url):
        domain = urlparse(url).netloc.lower()
        for priority in self.priority_domains:
            if priority.lower() in domain:
                return True
        return False

    def sanitize_filename(self, url):
        clean_url = urlparse(url).netloc + urlparse(url).path
        clean_url = clean_url.replace("/", "_").replace(":", "_").replace("?", "_").replace("&", "_")
        return clean_url[:150] + ".json"

    def is_relevant(self, text, url=""):
        """
        Filter Relevansi Dua Tingkat:
        - Domain prioritas (BPS, jurnal akademik, Kemensos): cukup ada keyword CORE
        - Domain lain (.id biasa): wajib ada Core DAN Context
        Min length: 400 karakter.
        """
        if len(text) <= 400:
            return False

        text_lower = text.lower()
        has_core = any(ck in text_lower for ck in self.core_keywords)

        if not has_core:
            return False

        # Domain prioritas = trusted source, cukup Core saja
        if url and self.is_priority(url):
            return True

        # Domain biasa = wajib ada Core + Context (lokasi/program)
        has_context = any(cx in text_lower for cx in self.context_keywords)
        return has_context

    def extract_content(self, url):
        # 1. Skip non-HTML files
        if any(url.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.zip', '.xlsx', '.ppt', '.pptx', '.jpg', '.png']):
            print(f"[-] Skipped (File Type): {url}")
            if self.notifier: self.notifier.on_skipped("File Type", url)
            return None

        # 2. Cek Duplikasi URL
        if url in self.visited_urls: 
            return None
        
        # 3. Cek Blocked Domain
        if self.is_blocked(url):
            print(f"[-] Skipped (Blocked/Noise Domain): {url}")
            if self.notifier: self.notifier.on_skipped("Blocked Domain", url)
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        try:
            print(f"[*] Extracting: {url}")
            response = requests.get(url, headers=headers, timeout=20, verify=False)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()

            # --- CABANG 1: PDF ---
            if 'application/pdf' in content_type:
                if not PDF_SUPPORT:
                    print(f"[-] Skipped (PDF - pdfplumber not installed): {url}")
                    if self.notifier: self.notifier.on_skipped("PDF no support", url)
                    return None
                print(f"[*] Parsing PDF: {url}")
                text_content = self._extract_pdf_text(response.content)
                if not text_content:
                    print(f"[-] Skipped (PDF empty/unreadable): {url}")
                    if self.notifier: self.notifier.on_skipped("PDF empty", url)
                    return None
                title = url.split('/')[-1] or "PDF Document"

            # --- CABANG 2: HTML ---
            elif 'text/html' in content_type:
                response.encoding = response.apparent_encoding
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else "No Title"
                for noise in soup(["script", "style", "nav", "footer", "header", "aside", "form", "button", "iframe"]):
                    noise.decompose()
                content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'article', 'section'])
                text_content = " ".join([tag.get_text().strip() for tag in content_tags if tag.get_text().strip()])

            # --- CABANG 3: Abaikan (bukan HTML/PDF) ---
            else:
                print(f"[-] Skipped (Unsupported Content-Type: {content_type}): {url}")
                if self.notifier: self.notifier.on_skipped("Content-Type", url)
                return None

            # 4. Validasi Konten (Stricter Filter)
            if not self.is_relevant(text_content, url):
                print(f"[-] Skipped (Not Relevant/Poor Quality): {url}")
                if self.notifier: self.notifier.on_skipped("Not Relevant", url)
                return None
            
            # 5. Cek Duplikasi Isi (Content Hashing)
            content_hash = self._get_hash(text_content)
            if content_hash in self.content_hashes:
                print(f"[-] Skipped (Duplicate Content): {url}")
                if self.notifier: self.notifier.on_skipped("Duplicate", url)
                return None

            # 6. Simpan dalam JSON
            quality = self.get_quality_score(text_content, url)
            data = {
                "metadata": {
                    "url": url,
                    "title": title.strip(),
                    "domain": urlparse(url).netloc,
                    "crawl_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source_type": self.get_source_type(url),   # government / academic / news
                    "quality_score": quality,                    # 0-100
                    "is_priority": self.is_priority(url)
                },
                "content": text_content
            }

            filename = self.sanitize_filename(url)
            with open(os.path.join(self.output_dir, filename), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            self.visited_urls.add(url)
            self._save_visited(url)   # Simpan ke file agar persistent
            self.content_hashes.add(content_hash)
            print(f"[+] Saved: {title.strip()[:60]}...")
            if self.notifier: self.notifier.on_saved(title.strip(), url, quality)
            return soup

        except Exception as e:
            print(f"[!] Error {url}: {e}")
            if self.notifier: self.notifier.on_error(url, str(e))
            return None

    def search_duckduckgo(self, query):
        """Mencari link dengan region Indonesia dan safesearch off."""
        print(f"[*] Searching DuckDuckGo: {query}")
        try:
            results = []
            with DDGS() as ddgs:
                # region="id-id" untuk hasil Indonesia, safesearch="off" untuk hasil lebih luas
                for r in ddgs.text(query, region="id-id", safesearch="off", max_results=15):
                    results.append(r['href'])
            
            print(f"[*] Found {len(results)} results.")
            return results
        except Exception as e:
            print(f"[!] Search Error: {e}")
            return []

if __name__ == "__main__":
    import urllib3
    import random
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ── SETUP BOT TELEGRAM ──────────────────────────────────────
    BOT_TOKEN = "8780918428:AAErUJSKU-dYHS4VSLNgg5y6LJW1fv5g6o4"
    BOT_CHAT_ID = 1303803107

    notifier = TelegramNotifier(token=BOT_TOKEN, chat_id=BOT_CHAT_ID)
    notifier.start_polling()   # Aktifkan /status dan /stop dari HP
    # ────────────────────────────────────────────────────────────

    crawler = WebCrawlerAI(notifier=notifier)

    if not crawler.search_keywords:
        print("[!] keyword.txt kosong! Silakan isi kata kunci.")
    else:
        notifier.on_start(len(crawler.search_keywords))
        cycle = 0

        # ── LOOP TERUS MENERUS sampai /stop dari Telegram atau Ctrl+C ──
        try:
            while not notifier.is_stop_requested():
                cycle += 1
                keywords = crawler.search_keywords.copy()
                random.shuffle(keywords)  # Acak urutan tiap siklus biar hasilnya beda
                print(f"\n[*] ===== SIKLUS KE-{cycle} ({len(keywords)} kata kunci) =====")
                notifier.send(f"\U0001f501 Siklus ke-{cycle} dimulai ({len(keywords)} kata kunci, dikocok ulang)")

                for q in keywords:
                    if notifier.is_stop_requested():
                        break

                    links = crawler.search_duckduckgo(q)
                    if not links:
                        print(f"[!] No links found for: {q}")
                    else:
                        for link in links:
                            if notifier.is_stop_requested():
                                break
                            crawler.extract_content(link)
                            time.sleep(2)

                    print("[*] Cooling down 5s before next keyword...")
                    time.sleep(5)

                print(f"[*] Siklus {cycle} selesai. Jeda 2 menit sebelum siklus berikutnya...")
                notifier.send(f"\u23f3 Siklus {cycle} selesai. Jeda 2 menit lalu lanjut siklus {cycle+1}...")
                # Jeda antar siklus agar DuckDuckGo tidak ban
                for _ in range(120):
                    if notifier.is_stop_requested():
                        break
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\n[!] Dihentikan manual (Ctrl+C).")

        notifier.on_finish()
        print(f"\n[!] Crawler berhenti. Total siklus selesai: {cycle}. Data ada di '{crawler.output_dir}'.")