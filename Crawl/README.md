# AITF Web Crawler

Sistem Web Crawler Otomatis berskala besar untuk mengumpulkan dataset teks berbahasa Indonesia (fokus wilayah Jawa Timur) guna keperluan Pre-training atau Fine-tuning Large Language Models (LLM).

Sistem beroperasi 24/7 di server menggunakan **arsitektur multi-instance** (beberapa proses crawler paralel), dikontrol jarak jauh via Telegram, dan mencadangkan data otomatis ke Google Drive.

---

## Struktur File dan Penjelasan

### Skrip Utama

| File | Keterangan |
|---|---|
| `bot_runner.py` | **Entry point utama — jalankan file ini.** Bertindak sebagai Supervisor: spawn beberapa subprocess `main.py` secara paralel, menerima perintah Telegram (`/run`, `/stop`, `/status`, dll.), mengelola jadwal upload otomatis, dan mengirim laporan berkala gabungan tiap 30 menit. |
| `main.py` | Mesin utama crawler. Mencari URL via DuckDuckGo, lalu mengunduh dan mengekstrak konten web secara paralel menggunakan `ThreadPoolExecutor`. Menggunakan `FileLock` agar aman dijalankan sebagai banyak proses sekaligus tanpa duplikasi data. |
| `bot_monitor.py` | Modul helper berisi class `TelegramNotifier`. Dipakai oleh `main.py` untuk mencatat statistik internal per instans (dokumen tersimpan, dilewati, error). Notif ke Telegram dimatikan dari sini — laporan gabungan diurus sepenuhnya oleh `bot_runner.py`. |
| `upload_drive.py` | Mengelola seluruh siklus upload ke Google Drive: kompresi `data_raw/` menjadi ZIP, hapus arsip lama di Drive, dan unggah arsip baru menggunakan OAuth2. Dipanggil oleh `bot_runner.py` secara terjadwal atau via perintah `/upload`. |
| `data_cleaner.py` | Memproses dan menormalisasi file `.md` hasil crawling di `data_raw/` menjadi format JSONL (`.jsonl`) yang siap digunakan untuk pelatihan LLM. Dijalankan secara terpisah setelah data terkumpul. |
| `count_tokens.py` | Menghitung estimasi total token dari semua file di `data_raw/` menggunakan tokenizer Qwen2.5-7B-Instruct. Berguna untuk memantau ukuran dataset sebelum training. |

---

### File Konfigurasi & Daftar

| File | Keterangan |
|---|---|
| `config.py` | **(Tidak di-commit ke GitHub)** File konfigurasi pusat berisi: Token Telegram Bot, Chat ID, ID Folder Google Drive, jumlah instans crawler (`NUM_INSTANCES`), jumlah thread per instans (`NUM_CRAWL_WORKERS`), dan interval upload. Wajib dibuat manual di setiap lingkungan. |
| `keyword.txt` | Daftar kata kunci pencarian (saat ini ~269 keyword). Mencakup topik kemiskinan, bansos, PKH, DTKS, demografi Jawa Timur, profil kecamatan, dan pekerjaan mayoritas per wilayah. |
| `blocked_domain.txt` | Blacklist domain yang tidak relevan (berita hiburan, chord lagu, dll.) agar hasil pencarian tetap fokus pada topik LLM yang diinginkan. |
| `domain_priority.txt` | Daftar domain pemerintahan dan akademik prioritas yang diberi bobot lebih tinggi dalam penilaian relevansi konten. |
| `requirements.txt` | Daftar seluruh dependensi Python yang diperlukan. Install dengan `pip install -r requirements.txt`. |

---

### File yang Dihasilkan Otomatis (tidak di-commit)

| File / Folder | Keterangan |
|---|---|
| `data_raw/` | Direktori output hasil crawling. Berisi file `.md` per artikel dengan format Markdown + metadata YAML frontmatter (URL, judul, sumber, skor relevansi). |
| `visited_urls.txt` | Rekaman semua URL yang sudah berhasil dikunjungi. Dibaca saat startup untuk mencegah duplikasi meskipun crawler di-restart. Dilindungi `FileLock` agar aman diakses banyak proses bersamaan. |
| `crawl_1.log` | Log dari instans crawler #1. Setiap instans punya log terpisah (`crawl_1.log`, `crawl_2.log`, dst.). |
| `crawl.log` | Log lama (dari versi single-instance sebelumnya). Tidak dipakai lagi tapi masih ada untuk referensi. |
| `dataset_card.md` | Metadata deskripsi dataset (auto-generated oleh data_cleaner). |

---

## Panduan Penggunaan

### 1. Instalasi Dependensi
```bash
pip install -r requirements.txt
```

### 2. Persiapan Konfigurasi (Wajib Dibuat Manual)

Buat file `config.py` di folder `Crawl/`:
```python
BOT_TOKEN             = "TOKEN_BOT_TELEGRAM_KAMU"
BOT_CHAT_ID           = 123456789          # Chat ID kamu
DRIVE_FOLDER_ID       = "ID_FOLDER_DRIVE"
SERVICE_ACCOUNT_FILE  = "amazing-city-*.json"
NUM_CRAWL_WORKERS     = 50
SEARCH_DELAY          = 5.0
UPLOAD_INTERVAL_HOURS = 3
NUM_INSTANCES         = 5   # Jumlah proses crawler paralel
```

Buat file `credentials.json` dari Google Cloud Console (OAuth 2.0 Client ID).

### 3. Autentikasi Google Drive (Hanya Sekali)

Jalankan di **laptop/komputer yang ada browser-nya** untuk menghasilkan `token.json`:
```bash
python upload_drive.py
```
Salin `token.json` yang dihasilkan ke server:
```bash
vi token.json  # paste isi file token.json dari laptop
```

### 4. Menjalankan Bot di Server

Disarankan menggunakan `screen` atau `tmux` agar tetap berjalan setelah SSH ditutup:
```bash
screen -S crawler
python bot_runner.py
# Ctrl+A lalu D untuk detach
```

---

## Perintah Telegram Bot

| Perintah | Fungsi |
|---|---|
| `/run` | Mulai semua instans crawler (sesuai `NUM_INSTANCES` di `config.py`) |
| `/stop` | Hentikan semua instans secara aman (graceful shutdown) |
| `/status` | Tampilkan status gabungan: jumlah instans aktif, dokumen, URL visited, estimasi token dataset |
| `/log` | Tampilkan 15 baris log terakhir dari setiap instans digabung |
| `/upload` | Upload `data_raw/` ke Google Drive sekarang (tanpa tunggu jadwal) |
| `/help` | Tampilkan daftar perintah |

**Laporan otomatis:** Bot mengirim 1 laporan gabungan setiap **30 menit** selama crawler berjalan.

---

## Arsitektur Sistem

```
bot_runner.py (Supervisor — 1 proses)
    │
    ├── main.py [Instans #1]  ──┐
    ├── main.py [Instans #2]    │
    ├── main.py [Instans #3]    ├── data_raw/         (Shared, aman)
    ├── main.py [Instans #4]    │   visited_urls.txt  (Shared + FileLock)
    └── main.py [Instans #N]  ──┘
```

- **Multi-Instance:** Beberapa proses `main.py` jalan serentak. Tiap instans punya 50 thread download paralel.
- **Anti Duplikasi:** `visited_urls.txt` dilindungi `FileLock` (OS-level) agar antar proses tidak tabrakan.
- **Anti Rate-Limit DDG:** Setiap instans start dengan delay berbeda (0s, 20s, 45s, 75s, dst.) agar tidak serempak hit DuckDuckGo.
- **Satu Laporan:** Semua instans bekerja diam-diam. Hanya `bot_runner.py` yang komunikasi ke Telegram.
- **Auto Upload:** `data_raw/` dikompres ZIP dan diunggah ke Google Drive setiap 3 jam otomatis (atau via `/upload`). Arsip lama dihapus otomatis.
