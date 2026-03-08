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
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from duckduckgo_search import DDGS
from filelock import FileLock
from bot_monitor import TelegramNotifier
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

# Direktori tempat main.py berada — semua path file dicari relatif ke sini
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class WebCrawlerAI:
    def __init__(
        self,
        output_dir="data_raw",
        blocked_file="blocked_domain.txt",
        priority_file="domain_priority.txt",
        keyword_file="keyword.txt",
        notifier=None,
        visited_file="visited_urls.txt",
        instance_id=1,
    ):
        # Resolve semua path relatif ke direktori script (bukan cwd)
        def _abspath(p):
            return p if os.path.isabs(p) else os.path.join(SCRIPT_DIR, p)

        self.output_dir   = _abspath(output_dir)
        self.visited_file = _abspath(visited_file)
        self.notifier     = notifier
        self.instance_id  = instance_id
        # Lock file di-simpan di-samping visited_urls.txt (nama: visited_urls.txt.lock)
        self._file_lock   = FileLock(self.visited_file + ".lock", timeout=10)
        blocked_file  = _abspath(blocked_file)
        priority_file = _abspath(priority_file)
        keyword_file  = _abspath(keyword_file)

        # ── Shared state (thread-safe) ─────────────────────────────────────
        self._hash_lock    = threading.Lock()
        self._write_lock   = threading.Lock()
        self._ddg_lock     = threading.Lock()   # satu search DuckDuckGo dalam satu waktu
        # _visited_lock hanya dipakai untuk in-memory set di proses ini.
        # Penulisan ke disk memakai FileLock (aman lintas proses).
        self._visited_lock = threading.Lock()

        self.visited_urls  = self._load_visited()
        self.content_hashes = set()

        # ── Konfigurasi domain & keyword ────────────────────────────────────
        self.blocked_domains   = self._load_list(blocked_file)
        self.priority_domains  = self._load_list(priority_file)
        self.search_keywords   = self._load_list(keyword_file)

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

    def _load_visited(self):
        """Baca visited_urls.txt pakai FileLocker agar aman saat multi-instans startup bersamaan."""
        try:
            with self._file_lock:
                if os.path.exists(self.visited_file):
                    with open(self.visited_file, 'r', encoding='utf-8') as f:
                        urls = {l.strip() for l in f if l.strip()}
                    print(f"[Instans-{self.instance_id}] Loaded {len(urls):,} visited URLs")
                    return urls
        except Exception as e:
            print(f"[Instans-{self.instance_id}] Gagal load visited: {e}")
        return set()

    def _save_visited(self, url):
        """Simpan URL ke disk menggunakan FileLock (aman lintas proses)."""
        with self._visited_lock:          # in-process lock (cepat)
            self.visited_urls.add(url)   # update in-memory set
        try:
            with self._file_lock:        # OS-level inter-process lock
                with open(self.visited_file, 'a', encoding='utf-8') as f:
                    f.write(url + '\n')
        except Exception as e:
            print(f"[Instans-{self.instance_id}] Gagal simpan visited: {e}")

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
        if len(text) <= 400:
            return False
        text_lower = text.lower()
        has_core   = any(ck in text_lower for ck in self.core_keywords)
        if not has_core:
            return False
        if url and self.is_priority(url):
            return True
        return any(cx in text_lower for cx in self.context_keywords)

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
    # EXTRACT CONTENT (dipanggil per thread)
    # =========================================================================

    def extract_content(self, url):
        # 1. Skip tipe file non-text
        if any(url.lower().endswith(ext) for ext in [
            '.doc', '.docx', '.zip', '.xlsx', '.ppt', '.pptx', '.jpg', '.png', '.gif', '.mp4'
        ]):
            if self.notifier: self.notifier.on_skipped("File Type", url)
            return None

        # 2. Cek duplikasi URL (thread-safe)
        with self._visited_lock:
            if url in self.visited_urls:
                return None

        # 3. Cek blocked domain
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
                response.encoding = response.apparent_encoding
                soup  = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string.strip() if soup.title else "No Title"
                for noise in soup(["script", "style", "nav", "footer",
                                   "header", "aside", "form", "button", "iframe"]):
                    noise.decompose()
                content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'article', 'section'])
                text_content = " ".join(
                    t.get_text().strip() for t in content_tags if t.get_text().strip()
                )
            else:
                if self.notifier: self.notifier.on_skipped("Content-Type", url)
                return None

            # 4. Filter relevansi
            if not self.is_relevant(text_content, url):
                if self.notifier: self.notifier.on_skipped("Not Relevant", url)
                return None

            # 5. Cek duplikasi konten (thread-safe)
            content_hash = self._get_hash(text_content)
            with self._hash_lock:
                if content_hash in self.content_hashes:
                    if self.notifier: self.notifier.on_skipped("Duplicate", url)
                    return None
                self.content_hashes.add(content_hash)

            # 6. Tandai visited (thread-safe)
            with self._visited_lock:
                self.visited_urls.add(url)
            self._save_visited(url)

            # 7. Simpan sebagai Markdown
            quality     = self.get_quality_score(text_content, url)
            source_type = self.get_source_type(url)
            prio        = self.is_priority(url)
            self._save_markdown(url, title, text_content, quality, source_type, prio)

            print(f"[✓] Saved (q={quality}): {title[:60]}")
            if self.notifier: self.notifier.on_saved(title, url, quality)
            return True

        except requests.exceptions.Timeout:
            print(f"[!] Timeout: {url}")
            if self.notifier: self.notifier.on_error(url, "Timeout")
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

    def run(self, stop_fn=None):
        """
        Arsitektur:
        - Keyword search     : sequential (DuckDuckGo rate-limit)
        - URL crawling       : parallel (ThreadPoolExecutor, NUM_CRAWL_WORKERS)
        """
        import random
        cycle = 0

        with ThreadPoolExecutor(max_workers=NUM_CRAWL_WORKERS, thread_name_prefix="crawl") as executor:
            while True:
                if stop_fn and stop_fn():
                    break

                cycle += 1
                keywords = self.search_keywords.copy()
                random.shuffle(keywords)
                print(f"\n[*] === SIKLUS KE-{cycle} ({len(keywords)} kata kunci) ===")
                if self.notifier:
                    self.notifier.send(
                        f"🔄 Siklus ke-{cycle} dimulai "
                        f"({len(keywords)} kata kunci, {NUM_CRAWL_WORKERS} crawl workers)"
                    )

                for q in keywords:
                    if stop_fn and stop_fn():
                        break

                    urls = self.search_duckduckgo(q)
                    if not urls:
                        time.sleep(SEARCH_DELAY)
                        continue

                    # Submit semua URL ke thread pool
                    futures = {executor.submit(self.extract_content, url): url for url in urls}
                    # CATATAN: tidak pakai timeout di as_completed karena
                    # tiap request sudah punya timeout=20s di dalam extract_content.
                    # Kalau pakai timeout di sini, TimeoutError bisa crash loop utama.
                    try:
                        for future in as_completed(futures):
                            try:
                                future.result()
                            except Exception as e:
                                print(f"[!] Worker exception: {e}")
                    except Exception as e:
                        print(f"[!] Unexpected error saat crawl batch: {e}")

                    # Jeda antar keyword agar DuckDuckGo tidak ban
                    if not (stop_fn and stop_fn()):
                        time.sleep(SEARCH_DELAY)

                if stop_fn and stop_fn():
                    break

                print(f"[*] Siklus {cycle} selesai. Jeda 2 menit ...")
                if self.notifier:
                    self.notifier.send(f"⏳ Siklus {cycle} selesai. Jeda 2 menit ...")

                for _ in range(120):
                    if stop_fn and stop_fn():
                        break
                    time.sleep(1)

        print(f"\n[✓] Crawler berhenti. Total siklus: {cycle}.")
        if self.notifier:
            self.notifier.on_finish()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import signal
    import traceback

    # Baca instance ID dan delay dari environment variable (diset oleh bot_runner.py)
    instance_id    = int(os.environ.get("CRAWLER_INSTANCE_ID", "1"))
    instance_delay = int(os.environ.get("CRAWLER_INSTANCE_DELAY", "0"))

    notifier = TelegramNotifier(token=config.BOT_TOKEN, chat_id=config.BOT_CHAT_ID)

    _stop_event = threading.Event()

    def _handle_sigterm(signum, frame):
        print(f"[Instans-{instance_id}] SIGTERM diterima — menghentikan crawler graceful...")
        _stop_event.set()

    signal.signal(signal.SIGTERM, _handle_sigterm)

    # Delay antar-instans agar tidak serempak hit DuckDuckGo (diset oleh bot_runner)
    if instance_delay > 0:
        print(f"[Instans-{instance_id}] Menunggu {instance_delay}s sebelum mulai (anti DDG rate-limit)...")
        for _ in range(instance_delay):
            if _stop_event.is_set():
                break
            time.sleep(1)

    crawler = WebCrawlerAI(notifier=notifier, instance_id=instance_id)

    if not crawler.search_keywords:
        print(f"[Instans-{instance_id}] keyword.txt kosong!")
    else:
        notifier.on_start(len(crawler.search_keywords))
        try:
            crawler.run(stop_fn=_stop_event.is_set)
        except KeyboardInterrupt:
            print(f"\n[Instans-{instance_id}] Dihentikan manual (Ctrl+C).")
        except BaseException as e:
            tb = traceback.format_exc()
            err_msg = (
                f"❌ <b>Crawler Instans-{instance_id} crash!</b>\n"
                f"<code>{type(e).__name__}: {str(e)[:200]}</code>\n\n"
                f"<pre>{tb[-1000:]}</pre>"
            )
            print(f"[Instans-{instance_id}] CRASH: {tb}")
            notifier.send(err_msg)
        finally:
            notifier.on_finish()
            print(f"[Instans-{instance_id}] Selesai. Data tersimpan di '{crawler.output_dir}'")
