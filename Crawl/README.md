# AITF Web Crawler

Proyek ini adalah sistem Web Crawler Otomatis berskala besar yang dirancang untuk mengumpulkan dataset teks berkualitas tinggi berbahasa Indonesia (khususnya untuk wilayah Jawa Timur). Data ini ditujukan untuk proses Pre-training atau Fine-tuning Large Language Models (LLM).

Sistem ini dirancang untuk berjalan secara paralel 24/7 di server, dikontrol jarak jauh melalui Telegram, dan mencadangkan data secara otomatis ke Google Drive dengan sistem rotasi yang efisien.

---

## Struktur Direktori dan File

```text
Crawl/
│
├── Konfigurasi Inti
│   ├── config.py           # (TIDAK ADA DI GIT) File pengaturan pusat: Token Telegram, Chat ID, ID Google Drive, Setting Thread.
│   ├── credentials.json    # (TIDAK ADA DI GIT) File rahasia OAuth 2.0 milik Google Cloud API.
│   └── token.json          # (Otomatis Dibuat) Token sesi Google Drive yang dihasilkan setelah otentikasi pertama.
│
├── Skrip Utama
│   ├── main.py             # Mesin utama crawler: Multi-threading pencarian DuckDuckGo & eksekusi request URL simultan.
│   ├── bot_runner.py       # (ENTRY POINT) Skrip yang HARUS dijalankan. Menjalankan main.py sebagai subprocess, menangani Telegram Bot, & Scheduler Upload.
│   ├── upload_drive.py     # Skrip logika kompresi data (ZIP), penghapusan file lama di Drive, dan upload OAuth2.
│   └── bot_monitor.py      # Modul pembantu untuk mengirim notifikasi Telegram secara sinkronus.
│
├── Pemrosesan Data
│   └── data_cleaner.py     # Skrip untuk menormalisasi markdown hasil crawl menjadi JSONL yang siap untuk pelatihan.
│
├── Daftar dan Kamus Crawler
│   ├── keyword.txt         # Daftar kata kunci utama pencarian topik (Pemerintahan, Bantuan Sosial, Kemiskinan Jawa Timur).
│   ├── blocked_domain.txt  # Daftar domain blacklist (situs berita umum, chord gitar) agar hasil pencarian relevan.
│   └── domain_priority.txt # URL spesifik pemerintahan yang diberi prioritas pencarian.
│
├── Penyimpanan Data (Dihasilkan oleh skrip)
│   ├── data_raw/           # Direktori hasil crawling. Berisi file `.md` (Markdown format + YAML Metadata).
│   ├── visited_urls.txt    # Rekaman URL yang sudah berhasil dicrawl (Pencegahan duplikasi persisten).
│   └── crawl.log           # File log sistem gabungan dari stdout dan stderr proses.
```

---

## Panduan Penggunaan Awal

**1. Instalasi Dependensi**
Pastikan terminal berada di dalam direktori `Crawl/`, kemudian jalankan perintah berikut:
```bash
pip install -r requirements.txt
```

**2. Persiapan File Konfigurasi (Tidak Boleh Di-Push ke GitHub)**
Diperlukan 2 file konfigurasi yang wajib dibuat secara manual di lingkungan kerja maupun server:
* `config.py` (Berisi pengaturan token bot telegram dan ID folder Drive).
* `credentials.json` (File kredensial OAuth2 dari Google Cloud API & Services).

**3. Otentikasi Google Drive (Hanya dilakukan satu kali)**
Otentikasi Google Drive diwajibkan menggunakan akun Google pengguna agar kapasitas penyimpanan yang digunakan sesuai dengan akun tersebut (misal: 2 TB). Jalankan skrip ini:
```bash
python upload_drive.py
```
*Proses ini akan membuka jendela browser untuk melakukan login Google. Setelah izin diberikan, token akses akan tersimpan ke dalam file `token.json` secara otomatis.*

**4. Menjalankan Bot dan Crawler**
Direkomendasikan untuk **tidak** menjalankan `main.py` secara langsung. Gunakan perintah di bawah ini (bisa dijalankan di dalam sesi `tmux` atau `screen` di server):
```bash
python bot_runner.py
```

---

## Perintah Telegram Bot

Setelah skrip `bot_runner.py` berjalan di server, bot Telegram siap menerima komando berikut:
- `/run` : Memulai mesin crawler di latar belakang.
- `/stop` : Menghentikan crawler secara aman (graceful shutdown) untuk memastikan integritas data.
- `/status` : Menampilkan informasi status operasional crawler secara langsung (waktu berjalan, jumlah file tersimpan, tautan terakhir).
- `/log` : Mengirimkan cuplikan 15 baris terakhir dari `crawl.log` yang ada di server.
- `/upload` : Memaksa sistem untuk segera mengompres direktori `data_raw/` dan mengunggahnya ke Google Drive pada saat itu juga (mengabaikan penjadwalan 3 jam).

---

## Konsep dan Arsitektur Sistem

- **Parallel Crawling**: Penarikan hasil pencarian (Keyword Search) melalui DuckDuckGo dilakukan secara sekuensial dengan jeda waktu untuk menghindari rate-limit atau pemblokiran IP. Namun, proses pengunduhan konten web dieksekusi menggunakan multi-threading yang beroperasi secara paralel untuk memaksimalkan kecepatan I/O.
- **Pencegahan Duplikasi Persisten**: Sistem mencatat riwayat kunjungan situs pada disk file (`visited_urls.txt`). Jika proses sistem terhenti dan dijalankan ulang, URL yang sudah direkam tidak akan dikunjungi lagi.
- **Manajemen Penyimpanan Drive Otomatis**: Ketika `upload_drive.py` diaktifkan oleh penjadwal atau perintah telegram, sistem akan secara otomatis menghapus file cadangan versi lama terlebih dahulu sebelum mengunggah file arsip zip yang baru. Mekanisme ini memastikan kapasitas Google Drive tidak penuh oleh arsip lama yang sudah kadaluarsa.
