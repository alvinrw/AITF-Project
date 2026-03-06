"""
bot_runner.py — Bot daemon yang jalan mandiri di server.
Jalankan: python bot_runner.py

Perintah dari Telegram:
  /run    → Mulai crawler (main.py)
  /stop   → Hentikan crawler
  /status → Lihat progress + info upload
  /log    → Lihat 20 baris terakhir log
  /upload → Upload data_raw ke Drive sekarang (tanpa tunggu jadwal)
"""

import requests
import subprocess
import threading
import time
import os
from datetime import datetime, timedelta
import config

# upload_drive diimport secara LAZY di dalam _do_upload_job()
_upload_available = None

BOT_TOKEN   = config.BOT_TOKEN
CHAT_ID     = config.BOT_CHAT_ID
BASE_URL    = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOG_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawl.log")
MAIN_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
DATA_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_raw")

UPLOAD_INTERVAL_HOURS = config.UPLOAD_INTERVAL_HOURS


# ─── Crawler State ───────────────────────────────────────────────────────────

crawler_proc  = None
last_update_id = 0
proc_lock     = threading.Lock()

# ─── Upload State ────────────────────────────────────────────────────────────

upload_lock       = threading.Lock()
_is_uploading     = False
_last_upload_time = None                                    # datetime | None
_next_upload_time = None                                    # datetime | None


# =============================================================================
# TELEGRAM HELPERS
# =============================================================================

def send(text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"[BOT] Gagal kirim: {e}")


def get_updates(offset):
    try:
        r = requests.get(
            f"{BASE_URL}/getUpdates",
            params={"offset": offset + 1, "timeout": 30},
            timeout=35,
        )
        return r.json().get("result", [])
    except Exception:
        return []


def skip_stale_updates():
    """Fetch update terbaru dan set last_update_id ke sana,
    sehingga semua perintah lama (misalnya /stop dari sesi kemarin)
    tidak ikut diproses saat bot restart."""
    global last_update_id
    try:
        r = requests.get(
            f"{BASE_URL}/getUpdates",
            params={"offset": -1, "timeout": 0},
            timeout=5,
        )
        results = r.json().get("result", [])
        if results:
            last_update_id = results[-1]["update_id"]
            print(f"[BOT] Skip {last_update_id} update lama dari sesi sebelumnya.")
    except Exception:
        pass  # Kalau gagal, lanjut dari 0


# =============================================================================
# LOG READER
# =============================================================================

def read_last_log(lines=20):
    if not os.path.exists(LOG_FILE):
        return "(log belum ada)"
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()
    return "".join(all_lines[-lines:]).strip()[-3000:] or "(log kosong)"


# =============================================================================
# STATUS BUILDER
# =============================================================================

def build_status():
    global crawler_proc, _last_upload_time, _next_upload_time, _is_uploading

    with proc_lock:
        running = crawler_proc is not None and crawler_proc.poll() is None

    state = "🟢 BERJALAN" if running else "🔴 BERHENTI"

    # Hitung dokumen tersimpan (.md dan .json)
    saved = 0
    if os.path.exists(DATA_DIR):
        saved = len([f for f in os.listdir(DATA_DIR)
                     if f.endswith(".md") or f.endswith(".json")])

    # Hitung visited URLs
    visited_file = os.path.join(os.path.dirname(__file__), "visited_urls.txt")
    visited = 0
    if os.path.exists(visited_file):
        with open(visited_file, "r") as vf:
            visited = sum(1 for _ in vf)

    # Info upload
    last_up = _last_upload_time.strftime("%d %b %Y %H:%M") if _last_upload_time else "-"
    next_up = _next_upload_time.strftime("%d %b %Y %H:%M") if _next_upload_time else "-"
    up_status = "⏳ Sedang upload…" if _is_uploading else f"⏰ Berikutnya: {next_up}"

    return (
        f"📊 <b>Status Crawler</b>\n"
        f"Status     : {state}\n"
        f"✅ Dokumen  : {saved} file tersimpan\n"
        f"🔗 Visited  : {visited} URL sudah dikunjungi\n"
        f"🕐 Waktu    : {datetime.now().strftime('%d %b %Y %H:%M:%S')}\n"
        f"\n"
        f"☁️ <b>Upload Drive</b>\n"
        f"Terakhir   : {last_up}\n"
        f"{up_status}"
    )


# =============================================================================
# UPLOAD LOGIC
# =============================================================================

def _do_upload_job():
    """Jalankan upload di thread terpisah (agar tidak blok bot polling)."""
    global _is_uploading, _last_upload_time, _next_upload_time, _upload_available

    with upload_lock:
        if _is_uploading:
            send("⚠️ Upload sedang berjalan, tunggu selesai dulu ya.")
            return
        _is_uploading = True

    try:
        # ── Lazy import: coba load upload_drive saat pertama kali dipakai ──
        try:
            from upload_drive import upload_data_raw
            _upload_available = True
        except ImportError as e:
            _upload_available = False
            send(
                f"❌ <b>Fitur upload tidak tersedia.</b>\n"
                f"Library Google belum terinstall di server.\n"
                f"Jalankan: <code>pip install google-api-python-client google-auth</code>\n"
                f"Error: {e}"
            )
            return

        class _SimpleNotifier:
            def send(self, msg): send(msg)   # noqa: F811

        upload_data_raw(folder_path=DATA_DIR, notifier=_SimpleNotifier())
        _last_upload_time = datetime.now()
        _next_upload_time = _last_upload_time + timedelta(hours=UPLOAD_INTERVAL_HOURS)
    finally:
        _is_uploading = False


def trigger_upload(reason="manual"):
    """Kirim notif lalu jalankan upload di background thread."""
    send(f"☁️ Upload diminta (<b>{reason}</b>). Mulai sekarang…")
    t = threading.Thread(target=_do_upload_job, daemon=True)
    t.start()


def upload_scheduler():
    """Thread background: upload otomatis tiap UPLOAD_INTERVAL_HOURS jam."""
    global _next_upload_time
    # Upload pertama setelah interval pertama berlalu
    _next_upload_time = datetime.now() + timedelta(hours=UPLOAD_INTERVAL_HOURS)
    print(f"[UPLOAD] Scheduler aktif — upload pertama: {_next_upload_time.strftime('%H:%M')}")

    while True:
        time.sleep(60)   # cek setiap menit
        if _next_upload_time and datetime.now() >= _next_upload_time and not _is_uploading:
            print("[UPLOAD] Jadwal upload terpicu.")
            trigger_upload(reason=f"otomatis tiap {UPLOAD_INTERVAL_HOURS} jam")


# =============================================================================
# CRAWLER CONTROL
# =============================================================================

def start_crawler():
    global crawler_proc
    with proc_lock:
        if crawler_proc and crawler_proc.poll() is None:
            return False, "Crawler sudah berjalan!"
        log_f = open(LOG_FILE, "a", encoding="utf-8")
        crawler_proc = subprocess.Popen(
            ["python", "-u", MAIN_SCRIPT],
            stdout=log_f,
            stderr=log_f,
            cwd=os.path.dirname(__file__),
        )
    return True, f"Crawler dimulai (PID: {crawler_proc.pid})"


def stop_crawler():
    global crawler_proc
    with proc_lock:
        if crawler_proc is None or crawler_proc.poll() is not None:
            return False, "Crawler tidak sedang berjalan."
        crawler_proc.terminate()
        try:
            crawler_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            crawler_proc.kill()
    return True, "Crawler dihentikan."


def monitor_crawler():
    global crawler_proc
    while True:
        time.sleep(30)
        with proc_lock:
            if crawler_proc and crawler_proc.poll() is not None:
                code = crawler_proc.returncode
                send(
                    f"⚠️ Crawler berhenti tidak terduga (exit code {code}).\n"
                    f"Kirim /run untuk mulai ulang."
                )
                crawler_proc = None


# =============================================================================
# COMMAND HANDLER
# =============================================================================

def handle_command(text):
    # Strip @botname suffix dari command (misal /help@SomeCrawlerBot → /help)
    raw_cmd = text.strip().lower().split()[0]
    cmd = raw_cmd.split("@")[0]

    if cmd in ("/run", "/start"):
        ok, msg = start_crawler()
        send(f"{'🚀' if ok else '⚠️'} {msg}\n\nKirim /status untuk pantau, /stop untuk hentikan.")

    elif cmd == "/stop":
        ok, msg = stop_crawler()
        send(f"{'⛔' if ok else '⚠️'} {msg}")

    elif cmd == "/status":
        send(build_status())

    elif cmd == "/log":
        log = read_last_log(20)
        send(f"📋 <b>20 Baris Terakhir Log:</b>\n<pre>{log[:3500]}</pre>")

    elif cmd == "/upload":
        # Upload on-demand (tidak tunggu jadwal 3 jam)
        trigger_upload(reason="perintah manual /upload")

    elif cmd == "/help":
        send(
            "📖 <b>Perintah Bot Crawler</b>\n\n"
            "/run    — Mulai crawler\n"
            "/stop   — Hentikan crawler\n"
            "/status — Lihat status crawler + info upload Drive\n"
            "/log    — Lihat log terbaru\n"
            f"/upload — Upload data_raw ke Drive <i>sekarang</i> (tanpa tunggu jadwal {UPLOAD_INTERVAL_HOURS} jam)\n"
            "/help   — Tampilkan bantuan ini"
        )
    else:
        send(f"Perintah tidak dikenal: {text}\nKetik /help untuk daftar perintah.")


# =============================================================================
# MAIN
# =============================================================================

def main():
    global last_update_id

    # Background threads
    threading.Thread(target=monitor_crawler,  daemon=True).start()
    threading.Thread(target=upload_scheduler, daemon=True).start()

    # ── Skip perintah lama SEBELUM mulai polling ─────────────────────────────
    # Tanpa ini, /stop atau /run dari sesi kemarin akan langsung dieksekusi
    # saat bot_runner restart, yang menyebabkan crawler langsung stop/start.
    skip_stale_updates()
    # ─────────────────────────────────────────────────────────────────────────

    send(
        "🤖 <b>Bot Runner aktif!</b>\n"
        "Perintah tersedia:\n"
        "/run    — Mulai crawler\n"
        "/stop   — Hentikan crawler\n"
        "/status — Lihat progress + info upload\n"
        "/log    — Lihat log terbaru\n"
        f"/upload — Upload data_raw sekarang (jadwal otomatis tiap {UPLOAD_INTERVAL_HOURS} jam)"
    )
    print("[BOT] Bot runner aktif, menunggu perintah...")

    while True:
        updates = get_updates(last_update_id)
        for upd in updates:
            last_update_id = upd["update_id"]
            msg    = upd.get("message", {})
            text   = msg.get("text", "").strip()
            sender = msg.get("chat", {}).get("id")

            if str(sender) != str(CHAT_ID):
                continue

            if text.startswith("/"):
                print(f"[CMD] {text} dari {sender}")
                handle_command(text)


if __name__ == "__main__":
    main()
