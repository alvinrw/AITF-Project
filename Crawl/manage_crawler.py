import os
import sys
import subprocess
import psutil
import signal
import io

# Setup Unicode handling for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def get_crawler_processes():
    """Find all running crawler processes."""
    crawlers = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline:
                continue
            
            # Look for main.py or bot_runner.py
            cmd_str = " ".join(cmdline).lower()
            if "python" in proc.info['name'].lower() and ("main.py" in cmd_str or "bot_runner.py" in cmd_str):
                crawlers.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return crawlers

def list_crawlers():
    crawlers = get_crawler_processes()
    if not crawlers:
        print("[-] Tidak ada proses crawler yang ditemukan.")
        return
    
    print(f"[*] Menemukan {len(crawlers)} proses crawler:")
    print("-" * 50)
    print(f"{'PID':<8} {'Name':<15} {'Command'}")
    print("-" * 50)
    for p in crawlers:
        try:
            cmd = " ".join(p.info['cmdline'])
            print(f"{p.info['pid']:<8} {p.info['name']:<15} {cmd[:60]}...")
        except:
            continue
    print("-" * 50)

def kill_crawlers():
    crawlers = get_crawler_processes()
    if not crawlers:
        print("[-] Tidak ada proses untuk dimatikan.")
        return
    
    print(f"[!] Akan mematikan {len(crawlers)} proses crawler...")
    for p in crawlers:
        try:
            print(f"[-] Mematikan PID {p.info['pid']}...")
            if sys.platform == "win32":
                p.kill() # kill is safer on windows for orphaned procs
            else:
                p.terminate()
        except:
            print(f"[!] Gagal mematikan PID {p.info['pid']}")
    
    print("[✓] Selesai.")

def show_status():
    print(f"[*] Status Folder Data:")
    data_dir = "data_raw"
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        md_files = [f for f in files if f.endswith('.md')]
        print(f"    - Folder '{data_dir}' ada.")
        print(f"    - Total file: {len(files)}")
        print(f"    - File Markdown (.md): {len(md_files)}")
    else:
        print(f"    - Folder '{data_dir}' tidak ditemukan.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan:")
        print("  python manage_crawler.py --list    : List semua proses crawler")
        print("  python manage_crawler.py --kill    : Matikan semua proses crawler")
        print("  python manage_crawler.py --status  : Cek status folder data")
        sys.exit(1)
    
    arg = sys.argv[1]
    if arg == "--list":
        list_crawlers()
    elif arg == "--kill":
        kill_crawlers()
    elif arg == "--status":
        show_status()
    else:
        print(f"[!] Argumen tidak dikenal: {arg}")
