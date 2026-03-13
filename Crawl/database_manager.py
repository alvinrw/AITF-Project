import sqlite3
import threading
import os

class DatabaseManager:
    def __init__(self, db_path="crawler_queue.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Tabel Antrean
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
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
            conn.commit()
            conn.close()

    def add_urls(self, urls, source="unknown"):
        """Menambahkan URL ke antrean jika belum ada di queue atau visited."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            added_count = 0
            for url in urls:
                url = url.strip()
                if not url: continue
                try:
                    cursor.execute("INSERT OR IGNORE INTO queue (url, source) VALUES (?, ?)", (url, source))
                    if cursor.rowcount > 0:
                        added_count += 1
                except:
                    pass
            conn.commit()
            conn.close()
            return added_count

    def get_next_batch(self, limit=10):
        """Mengambil batch URL 'pending' dan menandainya sebagai 'processing'."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, url FROM queue WHERE status = 'pending' LIMIT ?", (limit,))
            rows = cursor.fetchall()
            
            ids = [r[0] for r in rows]
            if ids:
                cursor.execute(f"UPDATE queue SET status = 'processing' WHERE id IN ({','.join(['?']*len(ids))})", ids)
            
            conn.commit()
            conn.close()
            return [r[1] for r in rows]

    def mark_completed(self, url):
        """Tandai URL selesai dan pindahkan ke tabel visited untuk deduplikasi."""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queue WHERE url = ?", (url,))
            cursor.execute("INSERT OR IGNORE INTO visited (url_hash, url) VALUES (?, ?)", (url_hash, url))
            conn.commit()
            conn.close()

    def mark_failed(self, url):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE queue SET status = 'failed' WHERE url = ?", (url,))
            conn.commit()
            conn.close()

    def get_stats(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM queue GROUP BY status")
            queue_stats = dict(cursor.fetchall())
            cursor.execute("SELECT COUNT(*) FROM visited")
            visited_count = cursor.fetchone()[0]
            conn.close()
            return {
                "pending": queue_stats.get("pending", 0),
                "processing": queue_stats.get("processing", 0),
                "failed": queue_stats.get("failed", 0),
                "visited": visited_count
            }
