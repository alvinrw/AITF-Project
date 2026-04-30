import requests
from bs4 import BeautifulSoup

# --- KONFIGURASI DEBUG ---
# Ganti URL dan Selektor sesuai target yang ingin diuji
URL_TES = "https://jatim.antaranews.com/berita/249960/dinsos-bangkalan-tekan-kemiskinan-melalui-dua-program"
SELEKTOR_TES = "div.post-content, article, .entry-content" # Bisa coba beberapa sekaligus
# -------------------------

def debug_scraper(url, selector):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print(f"[*] Mengambil data dari: {url}...")
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        title_web = soup.find("title").get_text(strip=True) if soup.find("title") else "Tanpa Judul"

        # Coba mencari elemen berdasarkan selektor
        target = soup.select_one(selector)
        filename = "debug_result.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Hasil Debug Selektor\n\n")
            f.write(f"- **URL:** {url}\n")
            f.write(f"- **Selektor yang diuji:** `{selector}`\n")
            f.write(f"- **Judul Halaman:** {title_web}\n\n")

            if target:
                # 1. Identifikasi Struktur (Membantu Anda melihat tag apa saja di dalam selektor)
                tags_found = set([tag.name for tag in target.find_all(True)])
                f.write(f"### Info Struktur\n")
                f.write(f"Tag yang ditemukan di dalam selektor: `{', '.join(tags_found)}`\n\n")

                # 2. Pembersihan Ringan (Hanya yang universal merusak teks)
                for trash in target.select("script, style, iframe"):
                    trash.decompose()

                # 3. Ekstraksi Teks Berdasarkan Paragraf (Lebih rapi untuk dibaca)
                paragraphs = target.find_all(['p', 'h1', 'h2', 'h3'])
                content_list = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                
                # Jika tidak ada <p>, gunakan stripped_strings sebagai fallback
                if not content_list:
                    content_list = list(target.stripped_strings)

                full_text = "\n\n".join(content_list)

                if full_text:
                    f.write("## STATUS: BERHASIL\n\n")
                    f.write(f"### Konten Terdeteksi:\n\n{full_text}")
                    print(f"[OK] Selesai! Silakan cek file: {filename}")
                else:
                    f.write("## STATUS: ELEMENT DITEMUKAN TAPI KOSONG\n")
                    print("[WARN] Konten teks tidak ditemukan di dalam selektor tersebut.")
            else:
                f.write("## STATUS: GAGAL\n\nSelektor tidak ditemukan di halaman ini.")
                print("[FAIL] Selektor salah atau elemen tidak ada.")

    except Exception as e:
        print(f"[ERROR] Terjadi Kesalahan: {e}")

if __name__ == "__main__":
    debug_scraper(URL_TES, SELEKTOR_TES)