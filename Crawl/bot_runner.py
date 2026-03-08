"""
bot_runner.py — Bot daemon yang jalan mandiri di server.
Jalankan: python bot_runner.py

Perintah dari Telegram:
  /run    → Mulai crawler (N instans paralel)
  /stop   → Hentikan semua instans crawler
  /status → Lihat progress gabungan + info upload
  /log    → Lihat log gabungan dari semua instans
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
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_FILE    = os.path.join(SCRIPT_DIR, "crawl_{}.log")  # format string per instans
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "main.py")
DATA_DIR    = os.path.join(SCRIPT_DIR, "data_raw")
NUM_INSTANCES = config.NUM_INSTANCES

UPLOAD_INTERVAL_HOURS = config.UPLOAD_INTERVAL_HOURS


# ─── Crawler State ───────────────────────────────────────────────────────────

crawler_procs  = []  # list of (instance_id, subprocess.Popen)
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

def read_last_log(lines=15):
    """Baca log dari semua instans crawler dan gabungkan."""
    combined = []
    for idx in range(1, NUM_INSTANCES + 1):
        log_path = LOG_FILE.format(idx)
        if not os.path.exists(log_path):
            continue
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        excerpt = "".join(all_lines[-lines:]).strip()
        if excerpt:
            combined.append(f"--- Instans #{idx} ---\n{excerpt}")
    return "\n\n".join(combined)[-3000:] if combined else "(log belum ada)"


# =============================================================================
# TOKEN ESTIMATOR
# =============================================================================

def estimate_tokens():
    """Estimasi cepat jumlah token dari semua file di data_raw/.
    Metode: total bytes / 3.7  (rata-rata empiris teks Indonesia dengan tokenizer Qwen2.5)
    Sangat cepat karena hanya baca metadata file, tidak baca isi konten.
    """
    if not os.path.exists(DATA_DIR):
        return 0
    total_bytes = 0
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".md") or fname.endswith(".json"):
            try:
                total_bytes += os.path.getsize(os.path.join(DATA_DIR, fname))
            except OSError:
                pass
    # Qwen2.5 tokenizer: ~3.7 byte per token untuk teks Indonesia UTF-8
    return int(total_bytes / 3.7)


# =============================================================================
# STATUS BUILDER
# =============================================================================

def build_status():
    global crawler_procs, _last_upload_time, _next_upload_time, _is_uploading

    with proc_lock:
        active = [(i, p) for i, p in crawler_procs if p.poll() is None]

    n_active = len(active)
    if n_active == 0:
        state = "🔴 BERHENTI"
    elif n_active < NUM_INSTANCES:
        state = f"🟡 SEBAGIAN ({n_active}/{NUM_INSTANCES} berjalan)"
    else:
        state = f"🟢 BERJALAN ({n_active}/{NUM_INSTANCES} instans)"

    pid_list = ", ".join(str(p.pid) for _, p in active) if active else "-"

    # Hitung dokumen tersimpan (.md dan .json)
    saved = 0
    if os.path.exists(DATA_DIR):
        saved = len([f for f in os.listdir(DATA_DIR)
                     if f.endswith(".md") or f.endswith(".json")])

    # Hitung visited URLs
    visited_file = os.path.join(SCRIPT_DIR, "visited_urls.txt")
    visited = 0
    if os.path.exists(visited_file):
        with open(visited_file, "r") as vf:
            visited = sum(1 for _ in vf)

    # Info upload
    last_up = _last_upload_time.strftime("%d %b %Y %H:%M") if _last_upload_time else "-"
    next_up = _next_upload_time.strftime("%d %b %Y %H:%M") if _next_upload_time else "-"
    up_status = "⏳ Sedang upload…" if _is_uploading else f"⏰ Berikutnya: {next_up}"

    # Estimasi token (cepat, berbasis ukuran file)
    token_est = estimate_tokens()
    if token_est >= 1_000_000:
        token_str = f"~{token_est / 1_000_000:.2f}M token"
    elif token_est >= 1_000:
        token_str = f"~{token_est / 1_000:.1f}K token"
    else:
        token_str = f"{token_est} token"

    return (
        f"📊 <b>Status Crawler</b>\n"
        f"Status     : {state}\n"
        f"PID        : {pid_list}\n"
        f"✅ Dokumen  : {saved} file tersimpan\n"
        f"🔗 Visited  : {visited} URL sudah dikunjungi\n"
        f"🪙 Estimasi : {token_str} (Qwen2.5)\n"
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
    """Spawn NUM_INSTANCES subprocess main.py dengan delay berbeda untuk hindari DDG rate-limit."""
    global crawler_procs
    # Delay antar instans agar tidak bersamaan nge-hit DDG
    DELAYS = [0, 20, 45, 75, 120]  # detik (cukup untuk 5 instans)
    with proc_lock:
        # Cek apakah sudah ada yang jalan
        still_running = [(i, p) for i, p in crawler_procs if p.poll() is None]
        if still_running:
            return False, f"{len(still_running)} instans crawler sudah berjalan!"

        crawler_procs = []
        pids = []
        for idx in range(1, NUM_INSTANCES + 1):
            delay = DELAYS[idx - 1] if idx - 1 < len(DELAYS) else (idx - 1) * 25
            log_path = LOG_FILE.format(idx)
            log_f = open(log_path, "a", encoding="utf-8")
            env = os.environ.copy()
            env["CRAWLER_INSTANCE_ID"] = str(idx)
            env["CRAWLER_INSTANCE_DELAY"] = str(delay)
            proc = subprocess.Popen(
                ["python", "-u", MAIN_SCRIPT],
                stdout=log_f,
                stderr=log_f,
                cwd=SCRIPT_DIR,
                env=env,
            )
            crawler_procs.append((idx, proc))
            pids.append(f"#{idx}=PID:{proc.pid}")

    return True, f"Sukses! {NUM_INSTANCES} instans dimulai: {', '.join(pids)}"


def stop_crawler():
    """Hentikan semua subprocess crawler yang sedang berjalan."""
    global crawler_procs
    with proc_lock:
        running = [(i, p) for i, p in crawler_procs if p.poll() is None]
        if not running:
            return False, "Tidak ada instans crawler yang sedang berjalan."
        for i, p in running:
            p.terminate()
        for i, p in running:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        crawler_procs = []
    return True, f"{len(running)} instans crawler dihentikan."


def monitor_crawler():
    global crawler_procs
    while True:
        time.sleep(30)
        with proc_lock:
            dead = [(i, p) for i, p in crawler_procs if p.poll() is not None]
        if dead:
            codes = ", ".join(f"#{i}(exit:{p.returncode})" for i, p in dead)
            send(
                f"⚠️ {len(dead)} instans crawler berhenti tidak terduga: {codes}.\n"
                f"Kirim /run untuk mulai ulang."
            )
            with proc_lock:
                crawler_procs = [(i, p) for i, p in crawler_procs if p.poll() is None]


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
# PERIODIC REPORTER (laporan gabungan 1x, bukan per-instans)
# =============================================================================

PERIODIC_REPORT_MINUTES = 30  # Kirim laporan gabungan setiap N menit

def periodic_reporter():
    """Kirim 1 laporan gabungan semua instans setiap PERIODIC_REPORT_MINUTES menit.
    Menggantikan notif per-instans yang spammy dari bot_monitor.py.
    """
    time.sleep(PERIODIC_REPORT_MINUTES * 60)  # Tunggu sebelum laporan pertama
    while True:
        with proc_lock:
            active = [(i, p) for i, p in crawler_procs if p.poll() is None]
        if active:  # Hanya kirim kalau ada yang jalan
            send(
                f"⏱ <b>Laporan Berkala ({PERIODIC_REPORT_MINUTES} menit)</b>\n\n"
                + build_status()
            )
        time.sleep(PERIODIC_REPORT_MINUTES * 60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    global last_update_id

    # Background threads
    threading.Thread(target=monitor_crawler,   daemon=True).start()
    threading.Thread(target=upload_scheduler,  daemon=True).start()
    threading.Thread(target=periodic_reporter, daemon=True).start()  # Laporan gabungan tiap 30 menit

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
