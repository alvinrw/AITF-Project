import os
import time
import json
import pdfplumber

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(SCRIPT_DIR, "PDF")
DATA_DIR = os.path.join(SCRIPT_DIR, "data_raw")
OUTPUT_FILE = os.path.join(DATA_DIR, "pdf_extract.jsonl")
PROCESSED_TRACKER = os.path.join(DATA_DIR, "processed_pdfs.txt")

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def load_processed():
    if not os.path.exists(PROCESSED_TRACKER):
        return set()
    with open(PROCESSED_TRACKER, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_processed(filename):
    with open(PROCESSED_TRACKER, 'a', encoding='utf-8') as f:
        f.write(filename + '\n')

def extract_pdf(pdf_path):
    text_content = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        return "\n".join(text_content).strip()
    except Exception as e:
        print(f"[PDF_EXTRACTOR] Gagal ekstrak {os.path.basename(pdf_path)}: {e}")
        return None

def main():
    print("[PDF_EXTRACTOR] Daemon berjalan, memindai folder PDF...")
    while True:
        processed = load_processed()
        pdf_files = []
        if os.path.exists(PDF_DIR):
            pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
        
        for filename in pdf_files:
            if filename in processed:
                continue
            
            pdf_path = os.path.join(PDF_DIR, filename)
            print(f"[PDF_EXTRACTOR] Memproses {filename}...")
            
            extracted_text = extract_pdf(pdf_path)
            
            if extracted_text and len(extracted_text) > 50:
                record = {
                    "url": f"local_pdf://{filename}",
                    "title": filename,
                    "text": extracted_text,
                    "source": "pdf_extract"
                }
                with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            # Catat bahwa sudah diproses (biar tidak extract ulang walau gagal)
            save_processed(filename)
            print(f"[PDF_EXTRACTOR] Selesai {filename}")
        
        time.sleep(60) # Scan setiap menit

if __name__ == "__main__":
    main()
