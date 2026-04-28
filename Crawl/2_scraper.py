import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

INPUT_FILE = "output.txt"
OUTPUT_DIR = "output_md"
SCRAPED_TRACKER = "scraper_state.txt"

# Pemetaan domain ke CSS Selector
DOMAIN_SELECTORS = {
    "jatim.antaranews.com": "div.wrap__article-detail-content.post-content",
    "malangtimes.com": "div.post-body",
    "cnbcindonesia.com": "div.detail-text",
    "detik.com": "div.detail__body-text.itp_bodycontent",
    "beritajatim.com": "div.post-content.cf.entry-content.content-spacious",
    "jawapos.com": "div.content-news",
    "surabaya.tribunnews.com": "div.side-article.txt-article.multi-fontsize.editcontent p",
    "kompas.com": "div.read__content",
    "katadata.co.id": "div.detail-body-article",
    "bisnis.com": ["div.col-7.col-leftm", "article.detailsContent.force-17.mt40"],
    "ekonomi.bisnis.com": ["div.col-7.col-left", "article.detailsContent.force-17.mt40"],
    "wartaekonomi.co.id": "div.articlePostContent.clearfix.lh-lg.mb-4",
    "medcom.id": "div#articleBody.text",
    "tribunnews.com": "div.side-article.txt-article.multi-fontsize.editcontent p",
    "jpnn.com": "div.page-content"
}

def clean_filename(title):
    # Membersihkan judul agar aman dijadikan nama file
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    return clean.strip()[:100]  # Batasi panjang nama file

def get_selector_for_domain(domain):
    for key, selector in DOMAIN_SELECTORS.items():
        if key in domain:
            return selector
    return None

def load_scraped_urls():
    if os.path.exists(SCRAPED_TRACKER):
        with open(SCRAPED_TRACKER, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def mark_as_scraped(url):
    with open(SCRAPED_TRACKER, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def scrape_url(url):
    domain = urlparse(url).netloc
    selector = get_selector_for_domain(domain)
    
    if not selector:
        print(f"[SKIP] Domain tidak didukung: {domain} -> {url}")
        return False

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Gagal mengakses {url}: {e}")
        return False

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Mencari elemen konten
    content_elements = []
    if isinstance(selector, list):
        # Jika ada beberapa kemungkinan selector (fallback)
        for sel in selector:
            elements = soup.select(sel)
            if elements:
                content_elements = elements
                break
    else:
        content_elements = soup.select(selector)

    if not content_elements:
        print(f"[SKIP] Selector '{selector}' tidak ditemukan di: {url}")
        return False

    # Ekstrak Judul
    title = "Tanpa Judul"
    h1_tag = soup.find('h1')
    if h1_tag:
        title = h1_tag.get_text(strip=True)
    elif soup.title:
        title = soup.title.get_text(strip=True)

    # Ekstrak Paragraf
    paragraphs = []
    for element in content_elements:
        # Jika selector menunjuk langsung ke tag <p>
        if element.name == 'p':
            text = element.get_text(strip=True)
            if len(text) >= 20:
                paragraphs.append(text)
        else:
            # Jika selector menunjuk ke container <div> atau <article>
            for p in element.find_all(['p', 'div']):
                # Hindari duplikasi teks nested
                if p.find('p'): continue 
                text = p.get_text(strip=True)
                if len(text) >= 20 and text not in paragraphs:
                    paragraphs.append(text)

    if not paragraphs:
        print(f"[SKIP] Tidak ada paragraf (>20 karakter) ditemukan di: {url}")
        return False

    # Menyimpan ke Markdown
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    safe_title = clean_filename(title)
    if not safe_title:
        safe_title = "artikel_tanpa_judul"
        
    # Tambahkan hash kecil dari URL agar nama file unik jika judul sama
    file_id = str(abs(hash(url)))[:6]
    filename = f"{safe_title}_{file_id}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Source:** {url}\n\n")
        f.write("---\n\n")
        for p in paragraphs:
            f.write(f"{p}\n\n")

    print(f"[SUCCESS] Tersimpan: {filename}")
    return True

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[!] File {INPUT_FILE} tidak ditemukan. Jalankan 1_crawler.py terlebih dahulu.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    scraped_urls = load_scraped_urls()
    total = len(urls)
    print(f"[*] Total URL di {INPUT_FILE}: {total}")
    print(f"[*] URL sudah diproses sebelumnya: {len(scraped_urls)}")

    for i, url in enumerate(urls):
        if url in scraped_urls:
            continue
            
        print(f"[{i+1}/{total}] Memproses: {url}")
        scrape_url(url)
        mark_as_scraped(url) # Tandai selesai (baik berhasil maupun gagal/skip) agar tidak diulang

    print("[*] Proses scraping selesai.")

if __name__ == "__main__":
    main()
