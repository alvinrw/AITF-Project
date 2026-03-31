import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Setup Chrome Options (biar lebih "manusiawi")
chrome_options = Options()
# chrome_options.add_argument("--headless") # Buka komen ini kalau mau jalan tanpa muncul jendela
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

SAVE_FOLDER = "bps_pdfs"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def download_pdf(session, url, filename):
    try:
        # Gunakan session yang sama dengan Selenium biar cookies-nya ikut
        res = session.get(url, stream=True, timeout=30)
        res.raise_for_status()
        
        # Bersihkan nama file dari karakter ilegal Windows
        clean_name = "".join([c for c in filename if c.isalnum() or c in (' ', '.', '_')]).rstrip()
        path = os.path.join(SAVE_FOLDER, clean_name)
        
        with open(path, "wb") as f:
            for chunk in res.iter_content(8192):
                f.write(chunk)
        print(f"    [✅] Berhasil: {clean_name}")
    except Exception as e:
        print(f"    [❌] Gagal download {url}: {e}")

# Buat session requests
s = requests.Session()

# Mulai Crawling
for page in range(1, 134):
    url = f"https://jatim.bps.go.id/id/publication?page={page}"
    print(f"\n[📄] Memproses Halaman {page}...")
    
    driver.get(url)
    time.sleep(5) # Kasih waktu Cloudflare buat 'tenang'
    
    # Ambil cookies dari Selenium masukin ke Requests
    for cookie in driver.get_cookies():
        s.cookies.set(cookie['name'], cookie['value'])

    # Cari kartu publikasi
    cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/publication/']")
    links = list(set([c.get_attribute("href") for c in cards]))

    for link in links:
        try:
            print(f"  [→] Mengintip: {link}")
            driver.get(link)
            time.sleep(3)

            # Ambil judul buat nama file
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
            
            # Cari tombol download
            pdf_button = driver.find_element(By.XPATH, "//a[contains(@href,'download.php')]")
            pdf_link = pdf_button.get_attribute("href")

            filename = f"{title[:50]}.pdf"
            download_pdf(s, pdf_link, filename)

        except Exception as e:
            print(f"  [⚠️] Skip: Tombol download nggak ketemu atau error: {e}")

driver.quit()
