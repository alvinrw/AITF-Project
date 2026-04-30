import os
import re
try:
    import pdfplumber
except ImportError:
    print("[ERROR] Modul pdfplumber belum diinstall. Jalankan: pip install pdfplumber")
    exit()

try:
    import docx
except ImportError:
    print("[ERROR] Modul python-docx belum diinstall. Jalankan: pip install python-docx")
    exit()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "data", "PDF")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "markdown")

def clean_text(text):
    # 1. Hapus Karakter Alien (Hanya sisakan karakter ASCII standar/printable)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text) 
    
    # 2. Hapus pola Daftar Isi (Contoh: "Latar Belakang .......... 1")
    # Mendeteksi baris yang memiliki banyak titik diikuti angka di akhir
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Jika baris mengandung titik-titik (minimal 3) diikuti angka, kita anggap Daftar Isi
        if re.search(r'\.{3,}\s*\d+', line):
            continue
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Bersihkan baris kosong ganda
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def main():
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        print(f"[INFO] Folder {INPUT_DIR} telah dibuat. Harap masukkan file PDF Anda ke dalamnya.")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Ambil file .pdf dan .docx
    doc_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf') or f.lower().endswith('.docx')]
    if not doc_files:
        print(f"[INFO] Tidak ada file berformat .pdf atau .docx di folder {INPUT_DIR}.")
        return

    total_processed = 0

    for filename in doc_files:
        file_path = os.path.join(INPUT_DIR, filename)
        
        # Buat nama output .md (hapus ekstensi asli entah .pdf atau .docx)
        base_name = os.path.splitext(filename)[0]
        output_filename = base_name + ".md"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Mencegah duplikasi: skip jika file MD sudah ada
        if os.path.exists(output_path):
            print(f"[SKIP] {output_filename} sudah ada. Melewati ekstrak {filename}.")
            continue
        
        print(f"[*] Mengekstrak dokumen: {filename}...")
        try:
            full_text = []
            
            if filename.lower().endswith('.pdf'):
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            full_text.append(clean_text(text))
                            
            elif filename.lower().endswith('.docx'):
                doc = docx.Document(file_path)
                for para in doc.paragraphs:
                    if para.text.strip():
                        full_text.append(clean_text(para.text))
            
            if not full_text:
                print(f"[WARN] Teks kosong atau tidak terdeteksi pada file: {filename}")
                continue

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {base_name}\n\n")
                f.write("\n\n".join(full_text))
                
            print(f"[SUCCESS] Tersimpan ke: {output_filename}")
            total_processed += 1
            
        except Exception as e:
            print(f"[ERROR] Gagal memproses file {filename}: {e}")

    print(f"\n[INFO] Proses selesai. Total {total_processed} dokumen berhasil diekstrak.")

if __name__ == "__main__":
    main()
