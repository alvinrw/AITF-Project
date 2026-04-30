# Web Crawler & Scraper Pipeline

Folder ini berisi pipeline lengkap untuk melakukan pencarian URL, mengekstrak artikel berita dari web, mengekstrak teks dari dokumen PDF, dan mengubah semuanya menjadi dataset berformat JSONL yang siap digunakan untuk pemrosesan machine learning.

## Struktur Folder

```text
Crawl/
├── data/                       # Folder untuk semua input dan output data
│   ├── keywords.txt            # Input kata kunci untuk crawler berita (web)
│   ├── scraper_state.txt       # Tracker otomatis artikel yang sudah di-scrape
│   ├── dataset.jsonl           # Hasil akhir yang sudah diformat dan dihitung tokennya
│   ├── urls/                   # Output dari crawler (list_url.txt, jurnal_keyword.txt, dll)
│   ├── PDF/                    # Masukkan file PDF/DOCX ke folder ini untuk diekstrak
│   └── markdown/               # Output hasil ekstraksi dari web scraper dan PDF extractor
│
├── crawler.py                  # Script 1: Mencari URL berita dari mesin pencari
├── scraper.py                  # Script 2: Mengekstrak isi artikel dari URL web
├── pdf_extractor.py            # Script 3: Mengekstrak isi dokumen dari file PDF & DOCX
├── crawlling_pdf.py            # Script Tambahan: Mencari dan men-download file PDF secara otomatis
├── formatter.py                # Script 4: Mengubah file .md menjadi dataset.jsonl
├── debug.py                    # Script untuk mengetes selektor website baru
├── upload_drive.py             # Script untuk mengupload hasil dataset ke Google Drive
├── config.py                   # Konfigurasi variabel untuk proses upload
├── credentials/                # Folder berisi file kredensial API (Google Drive, dll)
└── requirements.txt            # Daftar dependensi Python
```

---

## Cara Penggunaan

### 1. Ekstraksi dari Website (Web Scraper)
Alur ini digunakan untuk mengambil data berupa teks artikel berita langsung dari situs web.

- **A. Pencarian URL**
  Buka file `data/keywords.txt` dan isi dengan kata kunci. Jalankan crawler:
  ```bash
  python crawler.py
  ```
  [INFO] URL akan tersimpan di `data/urls/`.

- **B. Scraping Artikel**
  Setelah list URL terkumpul, ekstrak isinya menggunakan scraper:
  ```bash
  python scraper.py
  ```
  [INFO] Artikel web yang berhasil diambil akan disimpan di `data/markdown/` sebagai file `.md`. Script otomatis mengabaikan URL yang sudah pernah diproses.

  *Contoh Output Scraper (Teks Web):*
  ```markdown
  # Pemkot Malang sebut penanganan kemiskinan terapkan keseimbangan
  Source: https://jatim.antaranews.com/berita/...

  ---

  Pewarta: Ananto Pradana
  Editor: Astrid Faidlatul
  ...
  ```

### 2. Ekstraksi dari Dokumen (PDF & DOCX)
Alur ini difokuskan khusus untuk mengambil informasi berupa teks dari dokumen riset atau laporan berformat `.pdf` dan `.docx`.

- **A. Pencarian & Download PDF Otomatis**
  Buka file `data/urls/jurnal_keyword.txt` dan isi dengan keyword pencarian dokumen (filetype:pdf). Lalu jalankan:
  ```bash
  python crawlling_pdf.py
  ```
  [INFO] File akan otomatis terdownload ke folder `data/PDF/`. Script ini akan melewati file yang sudah pernah didownload.

- **B. Mengekstrak Teks Dokumen**
  Setelah file PDF/DOCX terkumpul di folder `data/PDF/`, jalankan:
  ```bash
  python pdf_extractor.py
  ```
  [INFO] Script akan mengekstrak teks, membersihkan **karakter alien** dan membuang bagian **Daftar Isi**, lalu menyimpannya sebagai file `.md` ke `data/markdown/`.

  *Contoh Output PDF Extractor (Teks Buku/Jurnal):*
  ```markdown
  # Laporan_Penanganan_Kemiskinan_2025
  
  BAB I PENDAHULUAN
  Kemiskinan merupakan isu strategis yang harus ditangani...
  ```

### 3. Pembuatan Dataset (Formatter)
Setelah seluruh data terkumpul di dalam folder `data/markdown/` (baik yang berasal dari web scraper maupun PDF extractor), langkah terakhir adalah menyatukannya ke dalam format JSONL.
```bash
python formatter.py
```
[INFO] Output akhirnya adalah `data/dataset.jsonl` yang siap pakai, lengkap beserta jumlah token dari masing-masing artikel/dokumen.

---

## 📦 Akses Dataset (Sample)
Bagi Anda yang ingin melihat atau menguji coba contoh hasil dari seluruh rangkaian pipeline ini, dataset dalam format `.jsonl` telah tersedia secara publik di Hugging Face:

👉 **[alvinrifky/AITF-dataset](https://huggingface.co/datasets/alvinrifky/AITF-dataset)**

> [!IMPORTANT]
> Dataset yang dibagikan di atas adalah **versi terbatas (sampel kecil)** untuk keperluan demonstrasi/testing, bukan merupakan keseluruhan data hasil crawling lengkap dari proyek ini.

---

## 🎯 Panduan Strategi Crawling & Scraping

### 1. Google Dork & Format Dork
Untuk menemukan artikel atau dokumen yang tepat, kita perlu merangkai kata kunci menggunakan teknik **Google Dorks**. 
Google Dork memungkinkan kita mempersempit hasil pencarian agar lebih relevan dengan memfilter berdasarkan *website* (domain spesifik), jenis file, dan kata kunci eksak.

**Format Dasar Dork:**
`"keyword" site:domain.com`

**Contoh:**
`"kecerdasan buatan" site:antaranews.com`

### 2. Target Website & CSS Selectors
Setelah *Crawler* mengumpulkan URL dari hasil pencarian Google Dork, proses selanjutnya adalah **Scraping**.
Setiap website memiliki struktur HTML (tema) yang berbeda-beda. Agar kita hanya mengambil **isi berita utama** (tanpa iklan, menu, atau footer), kita menggunakan **CSS Selectors** spesifik untuk tiap web.

Berikut adalah bocoran website utama yang kita *scrape* beserta CSS Selector-nya:

| Target Web | CSS Selector (Pembungkus Konten) |
| --- | --- |
| **ANTARA Jatim** | `div.wrap__article-detail-content.post-content` |
| **Malang Times** | `div.post-body` |
| **CNBC Indonesia** | `div.detail-text` |
| **Detik** | `div.detail__body-text.itp_bodycontent` |
| **Berita Jatim** | `div.post-content.cf.entry-content.content-spacious` |

### 3. Cara Merangkai Scraper Menggunakan CSS Selector
Bagaimana CSS Selector ini bekerja di dalam *scrapper* kita?
1. **Identifikasi Elemen:** Scrapper (menggunakan `BeautifulSoup`) akan mengunduh halaman web, lalu secara cerdas mencari letak elemen yang persis cocok dengan Selector di tabel atas. Misalnya, jika url berasal dari *Malang Times*, script akan menargetkan elemen `<div class="post-body">`.
2. **Ekstraksi Teks Bersih:** Setelah area artikel utama ditemukan, scraper mengekstrak seluruh teks di dalamnya (menggunakan metode `stripped_strings`), mengabaikan dan membuang elemen HTML kotor di sekitarnya.
3. **Penyimpanan (Formatter):** Teks yang didapat akan dirangkai kembali menjadi sebuah dokumen bersih dan di-save ke dalam format **Markdown (.md)** atau **JSONL**.

Strategi penargetan CSS khusus per-domain ini menjamin dataset yang dihasilkan murni teks berita asli tanpa sampah navigasi website, yang mana sangat penting untuk kualitas LLM!
