import os
import io
import re
import sys
import requests
import json
import time
import hashlib
import threading
import urllib3
from selectolax.parser import HTMLParser
from urllib.parse import urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from duckduckgo_search import DDGS
from filelock import FileLock
from bot_monitor import TelegramNotifier
from database_manager import DatabaseManager
import config

# Fix: Paksa print() di Windows menggunakan UTF-8 agar tidak crash
# saat mencetak karakter khusus/emoji ke console (menyebabkan UnicodeEncodeError).
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("[!] pdfplumber tidak ditemukan. Jalankan: pip install pdfplumber")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Konfigurasi jumlah worker ──────────────────────────────────────────────
NUM_CRAWL_WORKERS  = config.NUM_CRAWL_WORKERS
SEARCH_DELAY       = config.SEARCH_DELAY
REQUEST_DELAY      = 1.0  # detik antar request per thread (dalam lock)

# Cloudflare Config
CF_ACCOUNT_ID = getattr(config, 'CLOUDFLARE_ACCOUNT_ID', None)
CF_API_TOKEN  = getattr(config, 'CLOUDFLARE_API_TOKEN', None)

# Direktori tempat main.py berada — semua path file dicari relatif ke sini
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class WebCrawlerAI:
    def __init__(self, instance_id=1, keywords=None):
        self.instance_id = instance_id
        self.output_dir  = os.path.join(SCRIPT_DIR, "data_raw")
        os.makedirs(self.output_dir, exist_ok=True)

        self.db = DatabaseManager()
        self.notifier = TelegramNotifier(token=config.BOT_TOKEN, chat_id=config.BOT_CHAT_ID) if config.BOT_TOKEN else None
        
        # Keywords tetap disimpan untuk filter relevansi
        self.keywords = keywords or self._load_keywords()

        # ── Shared state (thread-safe) ─────────────────────────────────────
        self._write_lock   = threading.Lock()
        self._ddg_lock     = threading.Lock()   # satu search DuckDuckGo dalam satu waktu
        # _visited_lock hanya dipakai untuk in-memory set di proses ini.
        # Penulisan ke disk memakai FileLock (aman lintas proses).
        self._visited_lock = threading.Lock()

        # ── Konfigurasi domain & keyword ────────────────────────────────────
        self.blocked_domains   = self._load_list(os.path.join(SCRIPT_DIR, "config", "blocked_domain.txt"))
        self.priority_domains  = self._load_list(os.path.join(SCRIPT_DIR, "config", "domain_priority.txt"))
        self.search_keywords   = self._load_list(os.path.join(SCRIPT_DIR, "config", "keyword.txt"))

        # ── Filter relevansi ─────────────────────────────────────────────────
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
        self.context_keywords = [
            'jatim', 'jawa timur',
            'bps', 'sosial', 'bansos', 'bantuan', 'dana desa', 'puspa', 'pkh', 'dtks',
            'surabaya', 'malang', 'kediri', 'blitar', 'mojokerto', 'madiun',
            'probolinggo', 'pasuruan', 'batu', 'madura', 'bangkalan', 'sampang',
            'pamekasan', 'sumenep', 'sidoarjo', 'gresik', 'lamongan', 'tuban',
            'bojonegoro', 'jombang', 'nganjuk', 'magetan', 'ngawi', 'ponorogo',
            'pacitan', 'trenggalek', 'tulungagung', 'jember', 'banyuwangi',
            'situbondo', 'bondowoso', 'lumajang',
            'tapal kuda', 'mataraman', 'arek', 'pantura',
        ]

        os.makedirs(self.output_dir, exist_ok=True)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return [l.strip() for l in f if l.strip() and not l.startswith('#')]
        return []

    def _load_keywords(self):
        """Load keywords from keyword.txt."""
        keyword_file = os.path.join(SCRIPT_DIR, "config", "keyword.txt")
        return self._load_list(keyword_file)

    def _get_hash(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    # =========================================================================
    # KATEGORISASI & SCORING
    # =========================================================================

    def get_source_type(self, url):
        domain = urlparse(url).netloc.lower()
        if any(x in domain for x in ['go.id', 'tnp2k', 'bappeda', 'dinsos', 'kemensos', 'bps']):
            return 'government'
        if any(x in domain for x in ['ac.id', 'journal', 'ejournal', 'repository', 'jurnal']):
            return 'academic'
        return 'news'

    def get_quality_score(self, text, url):
        score      = 0
        text_lower = text.lower()
        score += min(40, len(text) // 100)
        core_hits  = sum(text_lower.count(ck) for ck in self.core_keywords)
        score += min(30, core_hits * 3)
        src = self.get_source_type(url)
        score += 30 if src == 'government' else (25 if src == 'academic' else 10)
        return min(100, score)

    # =========================================================================
    # FILTER DOMAIN
    # =========================================================================

    def is_indonesian_domain(self, url):
        domain = urlparse(url).netloc.lower()
        if domain.endswith('.id'):
            return True
        return any(p.lower() in domain for p in self.priority_domains)

    def is_blocked(self, url):
        domain = urlparse(url).netloc.lower()
        if any(x in domain for x in [
            'google.com', 'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com'
        ]):
            return True
        if any(b.lower() in domain for b in self.blocked_domains):
            return True
        return not self.is_indonesian_domain(url)

    def is_priority(self, url):
        domain = urlparse(url).netloc.lower()
        return any(p.lower() in domain for p in self.priority_domains)

    def is_relevant(self, text, url=""):
        if len(text) <= 500: # Diperketat, artikel terlalu pendek (di bawah 500 karakter) dibuang
            return False
            
        text_lower = text.lower()
        core_hits = sum(1 for ck in self.core_keywords if ck in text_lower)
        context_hits = sum(1 for cx in self.context_keywords if cx in text_lower)
        
        # Syarat Utama: Wajib ada Core Keyword (misal: "miskin", "bansos")
        if core_hits == 0:
            return False
            
        # Jika dari situs prioritas (Situs Resmi Jatim), syaratnya sedikit lebih longgar
        if url and self.is_priority(url):
            return True
            
        # Jika bukan situs prioritas, WAJIB ada persilangan antara Core + Context (misal: "Miskin" + "Jawa Timur")
        # Atau artikelnya sangat mendalam membahas kemiskinan (Core Hits >= 3)
        if context_hits > 0 or core_hits >= 3:
            return True
            
        return False

    # =========================================================================
    # EKSTRAKSI KONTEN
    # =========================================================================

    def _extract_pdf_text(self, response_content):
        if not PDF_SUPPORT:
            return None
        try:
            with pdfplumber.open(io.BytesIO(response_content)) as pdf:
                return " ".join(
                    p.extract_text().strip()
                    for p in pdf.pages
                    if p.extract_text()
                )
        except Exception as e:
            print(f"[!] PDF parse error: {e}")
            return None

    def sanitize_filename(self, url):
        clean = urlparse(url).netloc + urlparse(url).path
        clean = re.sub(r'[/:\?&]', '_', clean)
        return clean[:150] + ".md"

    # =========================================================================
    # SIMPAN KE MARKDOWN
    # =========================================================================

    def _save_markdown(self, url, title, text_content, quality, source_type, is_priority_flag):
        """Simpan konten ke file markdown dengan YAML frontmatter."""
        # Bersihkan title untuk YAML (hindari karakter : yang merusak parsing YAML)
        safe_title = title.replace(':', '-').replace('"', "'")
        frontmatter = (
            f"---\n"
            f"url: {url}\n"
            f"title: \"{safe_title}\"\n"
            f"domain: {urlparse(url).netloc}\n"
            f"crawl_date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"source_type: {source_type}\n"
            f"quality_score: {quality}\n"
            f"is_priority: {str(is_priority_flag).lower()}\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"{text_content}\n"
        )
        filename = self.sanitize_filename(url)
        filepath = os.path.join(self.output_dir, filename)
        with self._write_lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(frontmatter)

    # =========================================================================
    # CLOUDFLARE CRAWL INTEGRATION
    # =========================================================================

    def _fetch_via_cloudflare(self, url):
        """Panggil API Cloudflare Browser Rendering Crawl."""
        if not CF_ACCOUNT_ID or not CF_API_TOKEN:
            return None, None, False

        api_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/browser-rendering/crawl"
        headers = {
            "Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"url": url}

        try:
            print(f"[☁️] Cloudflare Fetching: {url}")
            resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    # Karena user ingin 'GASS' dan cepat, kita cetak Job ID 
                    print(f"[☁️] CF Job ID success: {data.get('result')}")
                    return data.get("result"), "text/html", True
            else:
                print(f"[!] Cloudflare Error ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"[!] Cloudflare Exception: {e}")
        return None, None, False

    # =========================================================================
    # EXTRACT CONTENT (dipanggil per thread)
    # =========================================================================

    def extract_content(self, url):
        # 1. Skip tipe file non-text
        if any(url.lower().endswith(ext) for ext in [
            '.doc', '.docx', '.zip', '.xlsx', '.ppt', '.pptx', '.jpg', '.png', '.gif', '.mp4'
        ]):
            if self.notifier: self.notifier.on_skipped("File Type", url)
            return None

        # 2. Cek blocked domain
        if self.is_blocked(url):
            if self.notifier: self.notifier.on_skipped("Blocked Domain", url)
            return None

        headers = {
            'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        try:
            print(f"[→] Fetching: {url}")
            response = requests.get(url, headers=headers, timeout=20, verify=False)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '').lower()

            # ── Cabang PDF ─────────────────────────────────────────────────
            if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                if not PDF_SUPPORT:
                    if self.notifier: self.notifier.on_skipped("PDF no support", url)
                    return None
                text_content = self._extract_pdf_text(response.content)
                if not text_content:
                    if self.notifier: self.notifier.on_skipped("PDF empty", url)
                    return None
                title = url.split('/')[-1] or "PDF Document"

            # ── Cabang HTML ────────────────────────────────────────────────
            elif 'text/html' in content_type:
                # Parsing cepat dengan Selectolax
                tree = HTMLParser(response.text)
                
                # Ekstrak Judul
                title_node = tree.css_first('title')
                title = title_node.text().strip() if title_node else "No Title"
                
                # [🕸️ SPIDER] RECURSIVE DISCOVERY
                # Ambil semua link dari halaman web ini dan masukkan ke antrean Database
                try:
                    from urllib.parse import urljoin, urlparse
                    
                    # Daftar domain/ekstensi yang diperbolehkan didapat dari prioritas config + go.id
                    allowed_domains = tuple(set(self.priority_domains + ['.go.id', '.ac.id', '.sch.id']))
                    
                    # Keyword Wajib di URL (Spider hanya merayap ke halaman yang URL-nya mengandung kata ini)
                    spider_keywords = (
                        'miskin', 'kemiskinan', 'poverty', 'bansos', 'pkh', 'blt', 'bantuan', 'sosial', 
                        'stunting', 'kesejahteraan', 'disabilitas', 'pengangguran', 'bpnt', 'dtks', 'desil', 
                        'kip', 'rentan', 'marjinal', 'subsidi', 'graduasi', 'dana-desa', 'puspa', 
                        'dinsos', 'bappeda', 'tnp2k', 'jatim', 'jawa-timur', 'kpm', 'ekstrem'
                    )
                    
                    new_links = set()
                    for a_tag in tree.css('a'):
                        href = a_tag.attributes.get('href')
                        if href:
                            abs_url = urljoin(url, href).split('#')[0]
                            # Filter: Harus HTTP/HTTPS
                            if abs_url.startswith('http'):
                                parsed = urlparse(abs_url)
                                domain = parsed.netloc.lower()
                                path_lower = parsed.path.lower()
                                
                                # Filter 1: Domain harus masuk dalam allowed_domains
                                if any(domain.endswith(d) for d in allowed_domains):
                                    # Filter 2: URL harus mengandung kata kunci kemiskinan/bantuan
                                    # ATAU berasal dari root domain khusus BPS/Kemensos tempat kumpulan data berada
                                    if any(kw in path_lower for kw in spider_keywords) or any(x in domain for x in ['bps.go.id', 'kemensos.go.id']):
                                        new_links.add(abs_url)
                    
                    if new_links:
                        # db.add_urls otomatis mengabaikan URL duplikat
                        added = self.db.add_urls(list(new_links), source="spider")
                        if added > 0:
                            print(f"    [🕸️] Spider menyedot {added} link RELEVAN dari {title[:25]}...")
                except Exception as e:
                    print(f"    [!] Spider Error: {e}")
                
                # Bersihkan elemen noise secara agresif
                selectors_to_remove = [
                    "script", "style", "nav", "footer", "header", 
                    "aside", "form", "button", "iframe", "noscript", ".ads", "#ads"
                ]
                for selector in selectors_to_remove:
                    for node in tree.css(selector):
                        node.decompose()
                
                # Ambil teks dari tag bermakna
                content_tags = tree.css('p, h1, h2, h3, article, section, div.content, .entry-content')
                text_content = " ".join(
                    t.text(separator=" ").strip() for t in content_tags if t.text().strip()
                )
            else:
                if self.notifier: self.notifier.on_skipped("Content-Type", url)
                return None

            # 4. Filter relevansi
            if not self.is_relevant(text_content, url):
                if self.notifier: self.notifier.on_skipped("Not Relevant", url)
                return None

            # 5. Cek duplikasi konten (thread-safe & persistent via SQLite DB)
            content_hash = self._get_hash(text_content)
            if not self.db.check_and_add_content_hash(content_hash):
                if self.notifier: self.notifier.on_skipped("Duplicate Content", url)
                return None

            # 6. Status visited dihandle oleh DatabaseManager.mark_completed/failed

            # 7. Hitung Skor Kualitas
            quality     = self.get_quality_score(text_content, url)
            
            # [FILTER KETAT] Buang artikel yang kualitasnya di bawah standar (Score < 35)
            if quality < 35:
                if self.notifier: self.notifier.on_skipped(f"Low Quality ({quality})", url)
                return None
                
            # 8. Simpan sebagai Markdown
            source_type = self.get_source_type(url)
            prio        = self.is_priority(url)
            self._save_markdown(url, title, text_content, quality, source_type, prio)

            print(f"[✓] Saved (q={quality}): {title[:60]}")
            if self.notifier: self.notifier.on_saved(title, url, quality)
            return True

        except requests.exceptions.Timeout:
            print(f"[!] Timeout: {url}")
            if self.notifier: self.notifier.on_error(url, "Timeout")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 403, 503) and CF_API_TOKEN:
                print(f"[🔄] Trigger Cloudflare Fallback for: {url}")
                job, _, ok = self._fetch_via_cloudflare(url)
                if ok:
                    return True  # Job CF berhasil disubmit, mark completed
            print(f"[!] HTTP Error {url}: {e}")
            if self.notifier: self.notifier.on_error(url, str(e))
        except Exception as e:
            print(f"[!] Error {url}: {e}")
            if self.notifier: self.notifier.on_error(url, str(e))
        return None

    # =========================================================================
    # SEARCH DUCKDUCKGO  (sequential — satu query dalam satu waktu)
    # =========================================================================

    def search_duckduckgo(self, query):
        print(f"[🔍] Searching: {query}")
        try:
            with self._ddg_lock:   # satu search dalam satu waktu
                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(query, region="id-id", safesearch="off", max_results=15):
                        results.append(r['href'])
            print(f"    → {len(results)} URL ditemukan")
            return results
        except Exception as e:
            print(f"[!] Search Error: {e}")
            return []

    # =========================================================================
    # RUN LOOP UTAMA  (search sequensial + crawl paralel)
    # =========================================================================

    def run(self):
        """Metode utama: Ambil URL dari SQLite dan crawl selamanya."""
        print(f"\n[🚀] Instance #{self.instance_id} Consumer aktif!")
        
        while True:
            # Ambil batch URL dari database
            batch_size = config.NUM_CRAWL_WORKERS * 20
            urls = self.db.get_next_batch(limit=batch_size)
            
            if not urls:
                # Kurangi sleep time agar responsif seperti saran
                print(f"[*] Instance #{self.instance_id}: Antrean kosong. Menunggu URL baru...")
                time.sleep(5) 
                continue
            
            print(f"[*] Instance #{self.instance_id} memproses batch {len(urls)} URL.")
            
            with ThreadPoolExecutor(max_workers=config.NUM_CRAWL_WORKERS) as executor:
                futures = {executor.submit(self.extract_content, url): url for url in urls}
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        result = future.result()
                        if result:
                            self.db.mark_completed(url)
                        else:
                            self.db.mark_failed(url)
                    except Exception as e:
                        print(f"[!] Worker Error {url}: {e}")
                        self.db.mark_failed(url)
            
            # Jeda antar batch demi kesehatan CPU/Koneksi
            time.sleep(2)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Ambil Instance ID dari env (diset oleh bot_runner)
    inst_id = int(os.environ.get("CRAWLER_INSTANCE_ID", 1))
    crawler = WebCrawlerAI(instance_id=inst_id)
    try:
        crawler.run()
    except KeyboardInterrupt:
        print(f"\n[Instans-{inst_id}] Dihentikan manual.")
    except Exception as e:
        print(f"[!] Error fatal di Instans-{inst_id}: {e}")
