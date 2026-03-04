import requests
import threading
import time
from datetime import datetime

class TelegramNotifier:
    """
    Bot Telegram untuk monitoring crawler secara remote.
    Mendukung:
    - Notifikasi otomatis (start, save, error, selesai)
    - Laporan berkala setiap N dokumen tersimpan
    - Perintah /status, /stop lewat Telegram
    """

    def __init__(self, token, chat_id=None):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self._stop_requested = False
        self._stats = {
            "saved": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": None,
            "last_url": "-",
        }
        # Laporan berkala: setiap N dokumen ATAU setiap M menit
        self.report_every = 3          # setiap 3 dokumen tersimpan
        self.report_every_minutes = 5  # setiap 5 menit
        self._last_report_time = time.time()


    # ─────────────────────── SETUP ────────────────────────

    def get_chat_id(self):
        """Ambil chat_id dari pesan terbaru ke bot (untuk setup awal)."""
        url = f"{self.base_url}/getUpdates"
        try:
            resp = requests.get(url, timeout=10).json()
            results = resp.get("result", [])
            if results:
                chat_id = results[-1]["message"]["chat"]["id"]
                print(f"[BOT] Chat ID kamu: {chat_id}  ← simpan ini di config!")
                return chat_id
            else:
                print("[BOT] Belum ada pesan masuk. Kirim /start ke bot dulu di Telegram.")
        except Exception as e:
            print(f"[BOT] Gagal ambil chat_id: {e}")
        return None

    # ─────────────────────── KIRIM PESAN ────────────────────────

    def send(self, message):
        """Kirim pesan ke Telegram. Gagal tidak crash program."""
        if not self.chat_id:
            return
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10
            )
        except Exception as e:
            print(f"[BOT] Gagal kirim pesan: {e}")

    def send_status(self):
        """Kirim ringkasan status sekarang."""
        stats = self._stats
        elapsed = ""
        if stats["start_time"]:
            secs = int(time.time() - stats["start_time"])
            h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
            elapsed = f"{h}j {m}m {s}d"

        msg = (
            f"📊 <b>Status Crawler</b>\n"
            f"🕐 Waktu jalan : {elapsed}\n"
            f"✅ Tersimpan   : {stats['saved']} dokumen\n"
            f"⏭ Dilewati    : {stats['skipped']}\n"
            f"❌ Error       : {stats['errors']}\n"
            f"🔗 URL terakhir:\n<code>{stats['last_url'][:80]}</code>"
        )
        self.send(msg)

    # ─────────────────────── UPDATE STATS ────────────────────────

    def on_start(self, keyword_count):
        self._stats["start_time"] = time.time()
        self._stop_requested = False
        now = datetime.now().strftime("%d %b %Y, %H:%M")
        self.send(
            f"🚀 <b>Crawler Mulai!</b>\n"
            f"📅 {now}\n"
            f"🔍 {keyword_count} kata kunci akan dicrawl."
        )

    def on_saved(self, title, url, quality_score):
        self._stats["saved"] += 1
        self._stats["last_url"] = url
        # Laporan berkala: setiap N dokumen ATAU setiap M menit
        minutes_passed = (time.time() - self._last_report_time) / 60
        if self._stats["saved"] % self.report_every == 0 or minutes_passed >= self.report_every_minutes:
            self.send_status()
            self._last_report_time = time.time()

    def on_skipped(self, reason, url):
        self._stats["skipped"] += 1
        self._stats["last_url"] = url

    def on_error(self, url, error_msg):
        self._stats["errors"] += 1
        self._stats["last_url"] = url

    def on_finish(self):
        self.send_status()
        self.send("🏁 <b>Crawler selesai!</b> Semua kata kunci sudah diproses.")

    # ─────────────────────── POLLING PERINTAH ────────────────────────

    def is_stop_requested(self):
        return self._stop_requested

    def start_polling(self):
        """Jalankan polling perintah di background thread."""
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        print("[BOT] Polling perintah Telegram aktif.")

    def _poll_loop(self):
        while True:
            try:
                resp = requests.get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": self.last_update_id + 1, "timeout": 30},
                    timeout=35
                ).json()

                for update in resp.get("result", []):
                    self.last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip().lower()
                    sender_id = msg.get("chat", {}).get("id")

                    # Hanya respon ke chat_id yang terdaftar
                    if str(sender_id) != str(self.chat_id):
                        continue

                    if text == "/status":
                        self.send_status()
                    elif text == "/stop":
                        self._stop_requested = True
                        self.send("⛔ <b>Stop diminta!</b> Crawler akan berhenti setelah URL saat ini selesai.")
                    elif text == "/start":
                        self.send("👋 Bot monitor aktif! Perintah yang tersedia:\n/status - Lihat progress\n/stop - Hentikan crawler")

            except Exception:
                time.sleep(5)
