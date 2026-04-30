import os
import re
try:
    import pdfplumber
except ImportError:
    print("[ERROR] Modul pdfplumber belum diinstall. Jalankan: pip install pdfplumber")
    exit()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "data", "PDF")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "markdown")

def clean_text(text):
    # Membersihkan baris kosong ganda
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def main():
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        print(f"[INFO] Folder {INPUT_DIR} telah dibuat. Harap masukkan file PDF Anda ke dalamnya.")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"[INFO] Tidak ada file berformat .pdf di folder {INPUT_DIR}.")
        return

    total_processed = 0

    for filename in pdf_files:
        pdf_path = os.path.join(INPUT_DIR, filename)
        output_filename = filename[:-4] + ".md"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Mencegah duplikasi: skip jika file MD sudah ada
        if os.path.exists(output_path):
            print(f"[SKIP] {output_filename} sudah ada. Melewati ekstrak {filename}.")
            continue
        
        print(f"[*] Mengekstrak dokumen: {filename}...")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(clean_text(text))
                
                if not full_text:
                    print(f"[WARN] Teks kosong atau tidak terdeteksi pada file: {filename}")
                    continue

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"# {filename[:-4]}\n\n")
                    f.write("\n\n".join(full_text))
                    
            print(f"[SUCCESS] Tersimpan ke: {output_filename}")
            total_processed += 1
            
        except Exception as e:
            print(f"[ERROR] Gagal memproses file {filename}: {e}")

    print(f"\n[INFO] Proses selesai. Total {total_processed} dokumen berhasil diekstrak.")

if __name__ == "__main__":
    main()
