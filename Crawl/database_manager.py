import sqlite3
import threading
import os

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "crawler_queue.db")

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path if db_path is not None else _DEFAULT_DB

        self._lock = threading.Lock()
        # Thread-local storage: setiap thread punya koneksi SQLite sendiri
        # yang dibuat sekali saja, jauh lebih efisien daripada buka/tutup tiap operasi.
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        """Kembalikan koneksi SQLite milik thread saat ini. Buat jika belum ada."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")  # Faster concurrent writes
        return self._local.conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            # Tabel Antrean
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    source TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Tabel Visited (untuk deduplikasi permanen)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visited (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT,
                    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Tabel Content Hashes (deduplikasi konten lintas proses, WAL-safe)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content_hashes (
                    hash TEXT PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def add_urls(self, urls, source="unknown"):
        """Menambahkan URL ke antrean jika belum ada di queue atau visited."""
        valid_urls = [u.strip() for u in urls if u.strip()]
        if not valid_urls:
            return 0

        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            records = [(u, source) for u in valid_urls]
            # Hitung before/after untuk rowcount yang akurat (executemany rowcount tidak reliable)
            cursor.execute("SELECT COUNT(*) FROM queue")
            before = cursor.fetchone()[0]
            try:
                cursor.executemany("INSERT OR IGNORE INTO queue (url, source) VALUES (?, ?)", records)
            except Exception:
                pass
            cursor.execute("SELECT COUNT(*) FROM queue")
            after = cursor.fetchone()[0]
            conn.commit()
            return max(0, after - before)

    def get_next_batch(self, limit=10):
        """Mengambil batch URL 'pending' dan menandainya sebagai 'processing'."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT id, url FROM queue WHERE status = 'pending' LIMIT ?", (limit,))
            rows = cursor.fetchall()
            ids = [r[0] for r in rows]
            if ids:
                cursor.execute(f"UPDATE queue SET status = 'processing' WHERE id IN ({','.join(['?']*len(ids))})", ids)
            conn.commit()
            return [r[1] for r in rows]

    def mark_completed(self, url):
        """Tandai URL selesai dan pindahkan ke tabel visited untuk deduplikasi."""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queue WHERE url = ?", (url,))
            cursor.execute("INSERT OR IGNORE INTO visited (url_hash, url) VALUES (?, ?)", (url_hash, url))
            conn.commit()

    def mark_failed(self, url):
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE queue SET status = 'failed' WHERE url = ?", (url,))
            conn.commit()

    def reset_stale_tasks(self):
        """Mengembalikan semua URL dengan status 'processing' kembali ke 'pending'."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE queue SET status = 'pending' WHERE status = 'processing'")
            affected = cursor.rowcount
            conn.commit()
            return affected

    def check_and_add_content_hash(self, content_hash):
        """Cek apakah hash konten sudah ada. Jika belum, tambahkan.
        Returns True jika BARU, False jika duplikat. Thread & proses safe via SQLite WAL."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO content_hashes (hash) VALUES (?)",
                (content_hash,)
            )
            conn.commit()
            return cursor.rowcount > 0  # 1 = baru, 0 = duplikat

    def get_stats(self):
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM queue GROUP BY status")
            queue_stats = dict(cursor.fetchall())
            cursor.execute("SELECT COUNT(*) FROM visited")
            visited_count = cursor.fetchone()[0]
            return {
                "pending": queue_stats.get("pending", 0),
                "processing": queue_stats.get("processing", 0),
                "failed": queue_stats.get("failed", 0),
                "visited": visited_count
            }
