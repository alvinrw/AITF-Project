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
from database_manager import DatabaseManager

# upload_drive diimport secara LAZY di dalam _do_upload_job()
_upload_available = None

BOT_TOKEN   = config.BOT_TOKEN
CHAT_ID     = config.BOT_CHAT_ID
BASE_URL    = f"https://api.telegram.org/bot{BOT_TOKEN}"
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_FILE    = os.path.join(SCRIPT_DIR, "logs", "crawl_{}.log")  # format string per instans
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "main.py")
DATA_DIR    = os.path.join(SCRIPT_DIR, "data_raw")
NUM_INSTANCES = config.NUM_INSTANCES

UPLOAD_INTERVAL_HOURS = config.UPLOAD_INTERVAL_HOURS


# ─── Crawler State ───────────────────────────────────────────────────────────

crawler_procs  = []  # list of (instance_id, subprocess.Popen)
last_update_id = 0
proc_lock     = threading.Lock()
engine_proc   = None  # Binary aitf-engine
importer_proc = None  # python url_importer.py
db_manager    = DatabaseManager()

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
    """Estimasi cepat jumlah token dari semua file di data_raw/ (RAW)."""
    if not os.path.exists(DATA_DIR):
        return 0
    total_bytes = 0
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".md") or fname.endswith(".json"):
            try:
                total_bytes += os.path.getsize(os.path.join(DATA_DIR, fname))
            except OSError:
                pass
    return int(total_bytes / 3.7)

def estimate_clean_tokens():
    """Estimasi cepat jumlah token dari data_training_cpt.jsonl (CLEAN)."""
    clean_file = os.path.join(SCRIPT_DIR, "data", "data_training_cpt.jsonl")
    if not os.path.exists(clean_file):
        return 0
    try:
        total_bytes = os.path.getsize(clean_file)
        return int(total_bytes / 3.7)
    except OSError:
        return 0


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

    # (visited_urls.txt sudah usang, kita gunakan statistik SQLite)

    # Statistik SQLite
    db_stats = db_manager.get_stats()
    
    # Info upload
    last_up = _last_upload_time.strftime("%d %b %Y %H:%M") if _last_upload_time else "-"
    next_up = _next_upload_time.strftime("%d %b %Y %H:%M") if _next_upload_time else "-"
    up_status = "⏳ Sedang upload…" if _is_uploading else f"⏰ Berikutnya: {next_up}"

    # Estimasi token (cepat, berbasis ukuran file)
    token_est_raw = estimate_tokens()
    token_est_clean = estimate_clean_tokens()
    
    t_raw_str = f"~{token_est_raw / 1_000_000:.2f}M" if token_est_raw >= 1_000_000 else f"~{token_est_raw / 1_000:.1f}K"
    t_clean_str = f"~{token_est_clean / 1_000_000:.2f}M" if token_est_clean >= 1_000_000 else f"~{token_est_clean / 1_000:.1f}K"

    # Cek status Engine & Importer
    global engine_proc, importer_proc
    engine_status = "🟢 Jalan" if (engine_proc and engine_proc.poll() is None) else "🔴 Berhenti"
    importer_status = "🟢 Jalan" if (importer_proc and importer_proc.poll() is None) else "🔴 Berhenti"

    return (
        f"📊 <b>Status Super-Crawler (Hybrid)</b>\n"
        f"🤖 Spider Engine : {engine_status}\n"
        f"🌉 URL Importer  : {importer_status}\n"
        f"👷 Worker Python : {state}\n"
        f"Worker PID : {pid_list}\n\n"
        f"🗄️ <b>Database URL (Anti-Duplikat)</b>\n"
        f"⏳ Pending    : {db_stats['pending']} (Menunggu Worker)\n"
        f"⚙️ Processing : {db_stats['processing']} (Sedang Dikerjakan)\n"
        f"✅ Completed  : {db_stats['visited']} (Sukses Tersimpan)\n"
        f"❌ Failed     : {db_stats['failed']} (Error/Dibuang)\n"
        f"🔗 <b>Total Visited</b>: {db_stats['visited'] + db_stats['failed']} URL\n\n"
        f"✅ Dokumen  : {saved} file tersimpan\n"
        f"🪙 <b>Estimasi Token (Qwen3.5)</b>\n"
        f"  ├ 🩸 Raw Data  : {t_raw_str}\n"
        f"  └ ✨ Clean Data: {t_clean_str}\n"
        f"🕐 Waktu: {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"☁️ <b>Upload Drive</b>\n"
        f"Terakhir: {last_up}\n"
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
        # 0. Jalankan Data Cleaner (Cleaning + Tokenization)
        send("🧹 Membersihkan data (DataCleaner) & Menghitung Token...")
        try:
            from data_cleaner import DataCleaner
            cleaner = DataCleaner(
                output_file=os.path.join(SCRIPT_DIR, "data", "data_training_cpt.jsonl")
            )
            cleaner.process_all()
        except Exception as e:
            send(f"⚠️ Gagal menjalankan DataCleaner: {e}")
            
        # 1. Jalankan Upload
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

        upload_data_raw(
            folder_path=DATA_DIR,
            clean_file=os.path.join(SCRIPT_DIR, "data", "data_training_cpt.jsonl"),
            notifier=_SimpleNotifier()
        )
        
        # 2. Jalankan Upload HuggingFace
        try:
            from upload_huggingface import upload_to_huggingface
            upload_to_huggingface(
                repo_id="alvinrifky/Crawling-MKN_1",
                folder_raw=DATA_DIR,
                clean_file=os.path.join(SCRIPT_DIR, "data", "data_training_cpt.jsonl"),
                notifier=_SimpleNotifier()
            )
        except Exception as e:
            send(f"⚠️ Gagal upload ke HuggingFace: {e}")
            
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
    """Spawn Engine, Importer, dan Workers."""
    global crawler_procs, engine_proc, importer_proc
    
    with proc_lock:
        still_running = [(i, p) for i, p in crawler_procs if p.poll() is None]
        if still_running:
            return False, "Sistem sudah berjalan!"

        # 1. Start AITF Engine (Binary) - SEKARANG MENGGUNAKAN LISENSI RESMI
        if os.name == 'nt':
            engine_bin = os.path.join(SCRIPT_DIR, "crawler-engine", "Windows", "aitf-engine.exe")
        else:
            engine_bin = os.path.join(SCRIPT_DIR, "crawler-engine", "Linux", "aitf-engine")
            
        try:
            # Pastikan ada daftar_keyword.txt agar engine tidak crash
            import shutil
            kw_src = os.path.join(SCRIPT_DIR, "config", "keyword.txt")
            # Engine binary membaca daftar_keyword.txt dari CWD (root Crawl/)
            kw_dst = os.path.join(SCRIPT_DIR, "daftar_keyword.txt")
            if os.path.exists(kw_src):
                shutil.copy2(kw_src, kw_dst)
                # Update juga config/ punya
                shutil.copy2(kw_src, os.path.join(SCRIPT_DIR, "config", "daftar_keyword.txt"))
                
            if os.path.exists(engine_bin):
                engine_proc = subprocess.Popen(
                    [engine_bin, "crawl", "--token", config.AITF_ENGINE_TOKEN], 
                    cwd=SCRIPT_DIR
                )
                print(f"[*] AITF Engine started. PID: {engine_proc.pid}")
            else:
                print(f"[!] GAGAL: File AITF Engine tidak ditemukan di: {engine_bin}")
                print("[!] (Pastikan file binary sudah diupload ke server dan ada di folder yang benar)")
                engine_proc = None
        except PermissionError:
            print(f"[!] GAGAL: Tidak ada izin eksekusi (Permission Denied) untuk {engine_bin}.")
            print(f"[!] (Jalankan: chmod +x {engine_bin})")
            engine_proc = None
        except Exception as e:
            print(f"[!] Gagal menyalakan AITF Engine: {e}")
            engine_proc = None

        # 2. Start URL Importer
        importer_script = os.path.join(SCRIPT_DIR, "url_importer.py")
        importer_proc = subprocess.Popen(["python", importer_script], cwd=SCRIPT_DIR)
        print(f"[*] URL Importer started. PID: {importer_proc.pid}")

        # 3. Start Consumer Workers
        crawler_procs = []
        for idx in range(1, NUM_INSTANCES + 1):
            log_path = LOG_FILE.format(idx)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            log_f = open(log_path, "a", encoding="utf-8")
            env = os.environ.copy()
            env["CRAWLER_INSTANCE_ID"] = str(idx)
            proc = subprocess.Popen(["python", "-u", MAIN_SCRIPT], stdout=log_f, stderr=log_f, cwd=SCRIPT_DIR, env=env)
            crawler_procs.append((idx, proc))

    return True, f"Sukses! Hybrid System Aktif ({NUM_INSTANCES} workers)."


def stop_crawler():
    """Hentikan semua subprocess crawler yang sedang berjalan."""
    global crawler_procs, engine_proc, importer_proc
    
    # ── JALANKAN OS KILL DULU ──
    # Membersihkan "orphan process" yang nyangkut karena bot_runner direstart 
    # saat engine-nya masih jalan di background.
    try:
        if os.name == 'nt':
            os.system("taskkill /F /IM aitf-engine.exe /T >nul 2>&1")
        else:
            os.system("pkill -9 -f aitf-engine >/dev/null 2>&1")
    except Exception:
        pass

    with proc_lock:
        running = [(i, p) for i, p in crawler_procs if p.poll() is None]

        # Cek apakah ada sesuatu yang masih jalan (worker ATAU engine/importer)
        engine_alive   = engine_proc   is not None and engine_proc.poll()   is None
        importer_alive = importer_proc is not None and importer_proc.poll() is None

        if not running and not engine_alive and not importer_alive:
            return True, "Memaksa OS membersihkan sisa proses Engine/Zombie yang tersangkut di background."

        # Hentikan Python workers
        for i, p in running:
            p.terminate()
        for i, p in running:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()

        # Hentikan Engine & Importer (selalu)
        if engine_proc:
            try:
                engine_proc.kill()
            except Exception:
                pass
            engine_proc = None
            
        if importer_proc:
            try:
                importer_proc.kill()
            except Exception:
                pass
            importer_proc = None

        crawler_procs = []

    stopped_parts = []
    if running:
        stopped_parts.append(f"{len(running)} worker")
    if engine_alive:
        stopped_parts.append("Spider Engine")
    if importer_alive:
        stopped_parts.append("URL Importer")
    return True, f"Dihentikan: {', '.join(stopped_parts)}."


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
        " <b>Bot Runner aktif!</b>\n"
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
