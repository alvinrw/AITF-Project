"""
bot_runner.py — Bot daemon yang jalan mandiri di server.
Jalankan: python bot_runner.py

Perintah dari Telegram:
  /run    → Mulai crawler (main.py)
  /stop   → Hentikan crawler
  /status → Lihat progress
  /log    → Lihat 20 baris terakhir log
"""

import requests
import subprocess
import threading
import time
import os
from datetime import datetime

BOT_TOKEN  = "8780918428:AAErUJSKU-dYHS4VSLNgg5y6LJW1fv5g6o4"
CHAT_ID    = 1303803107
BASE_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOG_FILE   = "crawl.log"
MAIN_SCRIPT = os.path.join(os.path.dirname(__file__), "main.py")

# ─── State ───────────────────────────────────────────────
crawler_proc = None          # subprocess.Popen object
last_update_id = 0
proc_lock = threading.Lock()

# ─── Telegram helpers ────────────────────────────────────

def send(text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"[BOT] Gagal kirim: {e}")

def get_updates(offset):
    try:
        r = requests.get(
            f"{BASE_URL}/getUpdates",
            params={"offset": offset + 1, "timeout": 30},
            timeout=35
        )
        return r.json().get("result", [])
    except Exception:
        return []

# ─── Log reader ──────────────────────────────────────────

def read_last_log(lines=20):
    if not os.path.exists(LOG_FILE):
        return "(log belum ada)"
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()
    tail = all_lines[-lines:]
    return "".join(tail).strip()[-3000:] or "(log kosong)"

# ─── Status builder ──────────────────────────────────────

def build_status():
    global crawler_proc
    with proc_lock:
        if crawler_proc is None:
            running = False
        else:
            running = crawler_proc.poll() is None   # None = masih jalan

    state = "🟢 BERJALAN" if running else "🔴 BERHENTI"

    # Hitung dokumen tersimpan
    data_dir = os.path.join(os.path.dirname(__file__), "data_raw")
    saved = len([f for f in os.listdir(data_dir) if f.endswith(".json")]) if os.path.exists(data_dir) else 0

    # Hitung visited URLs
    visited_file = os.path.join(os.path.dirname(__file__), "visited_urls.txt")
    visited = 0
    if os.path.exists(visited_file):
        with open(visited_file, "r") as vf:
            visited = sum(1 for _ in vf)

    return (
        f"📊 <b>Status Crawler</b>\n"
        f"Status     : {state}\n"
        f"✅ Dokumen  : {saved} file tersimpan\n"
        f"🔗 Visited  : {visited} URL sudah dikunjungi\n"
        f"🕐 Waktu    : {datetime.now().strftime('%d %b %Y %H:%M:%S')}"
    )

# ─── Crawler control ─────────────────────────────────────

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
            cwd=os.path.dirname(__file__)
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

# ─── Monitor thread (notif jika crawler crash) ───────────

def monitor_crawler():
    global crawler_proc
    while True:
        time.sleep(30)
        with proc_lock:
            if crawler_proc and crawler_proc.poll() is not None:
                code = crawler_proc.returncode
                send(f"⚠️ Crawler berhenti tidak terduga (exit code {code}).\nKirim /run untuk mulai ulang.")
                crawler_proc = None

# ─── Command handler ─────────────────────────────────────

def handle_command(text):
    cmd = text.strip().lower().split()[0]

    if cmd == "/run" or cmd == "/start":
        ok, msg = start_crawler()
        icon = "🚀" if ok else "⚠️"
        send(f"{icon} {msg}\n\nKirim /status untuk pantau, /stop untuk hentikan.")

    elif cmd == "/stop":
        ok, msg = stop_crawler()
        icon = "⛔" if ok else "⚠️"
        send(f"{icon} {msg}")

    elif cmd == "/status":
        send(build_status())

    elif cmd == "/log":
        log = read_last_log(20)
        send(f"📋 <b>20 Baris Terakhir Log:</b>\n<pre>{log[:3500]}</pre>")

    elif cmd == "/help":
        send(
            "📖 <b>Perintah Bot Crawler</b>\n\n"
            "/run    — Mulai crawler\n"
            "/stop   — Hentikan crawler\n"
            "/status — Lihat jumlah dokumen & status\n"
            "/log    — Lihat log terbaru\n"
            "/help   — Tampilkan bantuan ini"
        )
    else:
        send(f"Perintah tidak dikenal: {text}\nKetik /help untuk daftar perintah.")

# ─── Main polling loop ───────────────────────────────────

def main():
    global last_update_id
    threading.Thread(target=monitor_crawler, daemon=True).start()

    send(
        "🤖 <b>Bot Runner aktif!</b>\n"
        "Perintah tersedia:\n"
        "/run — Mulai crawler\n"
        "/stop — Hentikan crawler\n"
        "/status — Lihat progress\n"
        "/log — Lihat log terbaru"
    )
    print("[BOT] Bot runner aktif, menunggu perintah...")

    while True:
        updates = get_updates(last_update_id)
        for upd in updates:
            last_update_id = upd["update_id"]
            msg = upd.get("message", {})
            text = msg.get("text", "").strip()
            sender_id = msg.get("chat", {}).get("id")

            if str(sender_id) != str(CHAT_ID):
                continue   # Abaikan pesan dari orang lain

            if text.startswith("/"):
                print(f"[CMD] {text} dari {sender_id}")
                handle_command(text)

if __name__ == "__main__":
    main()
