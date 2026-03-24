import os
import sys

# Memastikan direktori script ada di PATH untuk memanggil module di level project
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from url_importer import URLImporter

def main():
    print("========================================")
    print("AITF URL Server Uploader")
    print("========================================")
    
    # URLImporter sudah di-setup agar me-load koneksi DB dan folder output "output/crawler_url.txt"
    importer = URLImporter()
    
    # Periksa apakah file crawler_url.txt ada di folder output/
    if not os.path.exists(importer.engine_output):
        print(f"[!] File {importer.engine_output} tidak ditemukan!")
        print("Silakan pindahkan file crawler_url.txt dari laptop ke dalam folder 'output/' di server ini.")
        sys.exit(1)
        
    print(f"[*] File ditemukan di '{importer.engine_output}'. Memulai proses import ke Database SQLite...")
    
    # Memanggil method built-in project untuk sinkronisasi URL dari TXT
    # Method ini membaca isi TXT, mendaftarkan ke database "crawler_queue.db",
    # lalu mengosongkan file TXT tersebut.
    importer.import_from_aitf_engine()
    
    print("\n[✓] Import selesai!")
    print("Bot kamu (`main.py`) secara otomatis akan mulai mencabik-cabik (crawl) URL yang barusan masuk!")
    
if __name__ == "__main__":
    main()
