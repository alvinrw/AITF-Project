import os
import glob
import sqlite3
import hashlib

def main():
    print("Mulai sinkronisasi data dari data_raw ke database...")
    db_path = os.path.join("data", "crawler_queue.db")
    raw_dir = "data_raw"
    
    if not os.path.exists(db_path):
        print("Database crawler_queue.db tidak ditemukan!")
        return
        
    md_files = glob.glob(os.path.join(raw_dir, "*.md"))
    print(f"Menemukan {len(md_files)} file .md. Mengekstrak URL...")
    
    records = []
    
    for file_path in md_files:
        try:
            # Baca 15 baris pertama untuk mencari YAML frontmatter 'url: ...'
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for _ in range(15):
                    line = f.readline()
                    if not line:
                        break
                    if line.startswith("url: "):
                        url = line.replace("url: ", "").strip()
                        if url:
                            url_hash = hashlib.md5(url.encode()).hexdigest()
                            records.append((url_hash, url))
                        break
        except Exception as e:
            print(f"Gagal membaca {file_path}: {e}")
            
    # Mencegah duplikasi di memori sebelum insert (opsional)
    unique_records = list(set(records))
    
    print(f"Berhasil mengekstrak {len(unique_records)} URL unik. Memasukkan ke database (Tabel 'visited')...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Gunakan INSERT OR IGNORE supaya kalau URL sudah ada, tidak terjadi error
        cursor.executemany("INSERT OR IGNORE INTO visited (url_hash, url) VALUES (?, ?)", unique_records)
        conn.commit()
        print(f"Selesai! {cursor.rowcount} URL baru sukses ditambahkan ke riwayat 'visited'.")
        print("Bot sekarang tahu bahwa URL-URL ini sudah pernah di-crawling.")
    except Exception as e:
        print(f"Error Database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
