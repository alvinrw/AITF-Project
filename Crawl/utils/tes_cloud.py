import requests
import json

CF_ACCOUNT_ID = "bdf9567f646438f890a10f6de9c42551"
# Gunakan token yang barusan muncul di curl verify tadi
CF_API_TOKEN = "jZrBtKElXCAuJsvCQpQdd1RiOvIgK08OHjqUPcAQ"

def test_cloudflare_crawl():
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/browser-rendering/crawl"
    
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Payload minimalis sesuai update terbaru
    payload = {
        "url": "https://example.com"
    }

    print("--- Menghubungi Robot Cloudflare (Versi Minimalis)... ---")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            print("[v] BERHASIL! Cloudflare merespon.")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"[X] GAGAL. Kode Status: {response.status_code}")
            print(f"Pesan Error: {response.text}")
            
    except Exception as e:
        print(f"[!] Terjadi error: {e}")

if __name__ == "__main__":
    test_cloudflare_crawl()