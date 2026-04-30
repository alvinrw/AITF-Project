import os
import time
import requests
import logging
from urllib.parse import urlparse, unquote
from duckduckgo_search import DDGS

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_safe_filename(url):
    """Mengekstrak nama file dari URL dan membersihkannya."""
    try:
        parsed_url = urlparse(url)
        # Ambil bagian paling akhir dari path URL
        filename = os.path.basename(unquote(parsed_url.path))
        if not filename or filename == "/":
            # Jika tidak ada nama, gunakan timestamp
            filename = f"document_{int(time.time())}.pdf"
            
        # Pastikan ekstensinya .pdf
        if not filename.lower().endswith('.pdf') and not filename.lower().endswith('.docx'):
            filename += ".pdf"
            
        # Bersihkan karakter yang tidak valid untuk nama file Windows/Linux
        valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        safe_filename = ''.join(c for c in filename if c in valid_chars)
        return safe_filename
    except:
        return f"document_{int(time.time())}.pdf"

def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    keyword_file = os.path.join(BASE_DIR, 'data', 'urls', 'jurnal_keyword.txt')
    output_dir = os.path.join(BASE_DIR, 'data', 'PDF')

    # Buat folder output jika belum ada
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(keyword_file):
        logging.error(f"File keyword tidak ditemukan: {keyword_file}")
        return

    with open(keyword_file, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    logging.info(f"Ditemukan {len(lines)} keyword jurnal/PDF.")

    total_downloaded = 0
    seen_urls = set()

    for idx, query in enumerate(lines, 1):
        logging.info(f"[{idx}/{len(lines)}] Mencari: {query}")

        try:
            with DDGS() as ddgs:
                # Batasi 3 hasil per keyword agar tidak diblokir DuckDuckGo
                results = ddgs.text(query, region='id-id', max_results=3)
                
                for item in results:
                    url = item.get('href', '')
                    if not url or url in seen_urls:
                        continue
                    
                    seen_urls.add(url)

                    # Pastikan kita hanya mencoba mendownload jika linknya mengindikasikan file dokumen
                    if '.pdf' in url.lower() or '.docx' in url.lower() or 'download' in url.lower() or 'file' in url.lower():
                        filename = get_safe_filename(url)
                        file_path = os.path.join(output_dir, filename)

                        # Skip jika file sudah pernah didownload sebelumnya
                        if os.path.exists(file_path):
                            logging.info(f"  [SKIP] File sudah ada: {filename}")
                            continue

                        logging.info(f"  [DOWNLOAD] Mengunduh: {url}")
                        
                        try:
                            # Set timeout dan header palsu (User-Agent) agar tidak ditolak server kampus
                            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                            response = requests.get(url, headers=headers, stream=True, timeout=15)
                            
                            # Cek apakah request sukses
                            if response.status_code == 200:
                                # Cek tipe konten, pastikan ukurannya wajar dan bukan HTML nyasar
                                content_type = response.headers.get('content-type', '').lower()
                                if 'text/html' not in content_type:
                                    with open(file_path, 'wb') as pdf_file:
                                        for chunk in response.iter_content(chunk_size=8192):
                                            pdf_file.write(chunk)
                                    total_downloaded += 1
                                    logging.info(f"  [SUCCESS] Tersimpan: {filename}")
                                else:
                                    logging.warning(f"  [FAILED] Link bukan file PDF melainkan halaman HTML.")
                            else:
                                logging.warning(f"  [FAILED] HTTP {response.status_code}")
                                
                        except Exception as e:
                            logging.error(f"  [ERROR] Gagal download: {str(e)[:50]}")
                            
                        # Jeda antar download agar server target tidak down / nge-blokir kita
                        time.sleep(2)

        except Exception as e:
            logging.error(f"Error saat mencari keyword: {e}")
            logging.info("Tidur 10 detik karena kemungkinan kena limit pencarian (rate limit).")
            time.sleep(10)

        # Jeda pencarian antar keyword
        time.sleep(3)

    logging.info(f"Selesai! Total file berhasil diunduh: {total_downloaded}")

if __name__ == "__main__":
    main()
