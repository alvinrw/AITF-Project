import requests
from bs4 import BeautifulSoup

def main():
    print("="*50)
    print("      Cek CSS Selector Berita     ")
    print("="*50)
    
    url = input("\nMasukkan URL berita: ").strip()
    if not url:
        print("[!] URL tidak boleh kosong.")
        return
        
    selector = input("Masukkan CSS Selector (misal: div.detail-text): ").strip()
    if not selector:
        print("[!] Selector tidak boleh kosong.")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("\n[*] Mengunduh halaman...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Gagal mengakses URL: {e}")
        return

    print("[*] Memparsing HTML...")
    soup = BeautifulSoup(response.text, "html.parser")
    
    elements = soup.select(selector)
    
    if not elements:
        print(f"\n[HASIL] GAGAL. Tidak ditemukan elemen dengan selector: '{selector}'")
        return
        
    print(f"\n[HASIL] SUKSES! Ditemukan {len(elements)} elemen menggunakan selector tersebut.")
    
    print("\n" + "-"*30)
    print("CUPLIKAN TEKS YANG DIEKSTRAK (Paragraf >= 20 karakter):")
    print("-" * 30)
    
    paragraphs = []
    for element in elements:
        if element.name == 'p':
            text = element.get_text(strip=True)
            if len(text) >= 20:
                paragraphs.append(text)
        else:
            for p in element.find_all(['p', 'div']):
                if p.find('p'): continue
                text = p.get_text(strip=True)
                if len(text) >= 20 and text not in paragraphs:
                    paragraphs.append(text)
                    
    if not paragraphs:
        print("\n[!] Selector ditemukan, namun tidak ada paragraf teks panjang di dalamnya.")
    else:
        for i, p in enumerate(paragraphs[:5]): # Tampilkan maksimal 5 paragraf pertama
            print(f"[{i+1}] {p[:150]}...")
            
        if len(paragraphs) > 5:
            print(f"... dan {len(paragraphs) - 5} paragraf lainnya.")

if __name__ == "__main__":
    main()
