# AITF Web Crawler 🕸️🤖

Proyek ini adalah sistem **Web Crawler Otomatis** berskala besar yang dirancang khusus untuk mengumpulkan dataset teks berkualitas tinggi berbahasa Indonesia (khususnya untuk wilayah Jawa Timur). Data ini ditujukan untuk proses *Pre-training* atau *Fine-tuning* Large Language Models (LLM).

Sistem ini sanggup berjalan paralel 24/7 di server, dikontrol jarak jauh lewat Telegram, dan membackup data secara real-time ke Google Drive dengan sistem rotasi efisien!

---

## 📁 Struktur File & Direktori

```text
Crawl/
│
├── ⚙️ Konfigurasi Inti
│   ├── config.py           # (TIDAK ADA DI GIT) File pengaturan pusat: Token Telegram, Chat ID, ID Google Drive, Setting Thread.
│   ├── credentials.json    # (TIDAK ADA DI GIT) File rahasia OAuth 2.0 milik Google Cloud API.
│   └── token.json          # (Otomatis Dibuat) Token sesi Google Drive yang digenerate setelah login pertama.
│
├── 🚀 Scripts Utama
│   ├── main.py             # Mesin utama crawler: Multi-threading pencarian DuckDuckGo & eksekusi request URL simultan.
│   ├── bot_runner.py       # (ENTRY POINT) Script yang HARUS di-run. Menjalankan main.py sebagai subprocess, handle Telegram Bot, & Scheduler Upload.
│   ├── upload_drive.py     # Script logic pemampatan data (ZIP), penghapusan file lama di Drive, dan upload OAuth2.
│   └── bot_monitor.py      # Module helper class untuk push notifikasi Telegram secara sinkronus.
│
├── 🛠️ Data Processing
│   └── data_cleaner.py     # Script untuk menormalisasi markdown hasil crawl menjadi JSONL siap training.
│
├── 🗃️ Daftar / Kamus Crawler
│   ├── keyword.txt         # 200+ Daftar kata kunci utama pencarian topik (Pemerintah, Bansos, Kemiskinan Jatim).
│   ├── blocked_domain.txt  # Daftar domain blacklist (kompas, tribun, situs chord agar hasil tidak berupa spam berita SEO).
│   └── domain_priority.txt # URL spesifik pemerintahan yang diberi prioritas crawler (jatimprov, bojonegorokab, dll).
│
├── 📂 Penyimpanan (Digenerate oleh script)
│   ├── data_raw/           # Direktori hasil crawling. Berisi jutaan file `.md` (Markdown format + YAML Metadata).
│   ├── visited_urls.txt    # Rekaman URL yang sudah berhasil dicrawl (Anti-Duplikasi meskipun server restart).
│   └── crawl.log           # File log sistem gabungan dari stdout / stderr process.
```

---

## 🚀 Cara Menjalankan Pertama Kali

**1. Install Dependensi**
Pastikan kamu berada di dalam folder `Crawl/`, lalu jalankan:
```bash
pip install -r requirements.txt
```

**2. Siapkan File Rahasia (Jangan Di-Push ke GitHub)**
Kamu butuh 2 file yang **wajib** dibuat manual di komputermu dan di server:
* `config.py` (Berisi pengaturan token bot telegram dan ID folder Drive).
* `credentials.json` (File rahasia OAuth2 dari Google Cloud *API & Services*).

**3. Otentikasi Google Drive (Pertama Kali Saja)**
Sebelum bot berjalan, kita butuh login Google Drive dari akun aslimu agar kuota 2TB-mu terbaca:
```bash
python upload_drive.py
```
*Ini akan membuka link browser, pilih akun Google kamu, "Allow", dan token akan tersimpan ke `token.json` otomatis.*

**4. Jalankan Bot Runner!**
Jangan pernah me-run `main.py` secara langsung. Selalu gunakan komando ini (bisa dipasang di `tmux`/`screen` pada server):
```bash
python bot_runner.py
```

---

## 📱 Perintah Telegram Bot (Remote Control)

Setelah script `bot_runner.py` nyala di server, buka bot Telegram-mu dan gunakan komando ini:
- `/run` : Menyalakan Crawler Engine di Background.
- `/stop` : Menghentikan Crawler (Graceful Shutdown - data tersimpan aman).
- `/status` : Menampilkan log real-time performa crawling (jumlah file tersimpan, cycle, jam operasi).
- `/log` : Mengirim cuplikan 15 baris terakhir dari `crawl.log` internal server.
- `/upload` : Memaksa sistem untuk segera mem-zip `data_raw/` dan mengirimnya ke Google Drive sekarang juga (Bypass scheduler 3 jam).

---

## 🧠 Konsep Arsitektur Menarik!

- **Parallel Crawling**: DuckDuckGo sangat rentan ban IP jika di-hit paralel, karena itu fase pencarian *URL Link* bersifat berurutan (sequential) dengan jeda 5 detik antar pencarian. Namun proses Download halaman web (*Extract Content*) menggunakan multi-threading berkapasitas 50 thread CPU secara paralel untuk kecepatan tinggi!
- **Anti-Duplikasi Absolute**: Tidak seperti database memori biasa, riwayat kunjungan disimpan di disk (`visited_urls.txt`). Jika server mati mendadak dan di-restart besoknya melalui `/run`, crawler tidak akan pernah mengunduh artikel lama yang sama dua kali!
- **Drive Smart Rotator**: Ketika `upload_drive.py` berjalan tiap 3 jam (maupun lewat commad /upload), dia akan terbang terlebih dahulu ke Google Drive untuk **menghapus master file zip lama** sebelum menaikkan zip baru. Menjamin Drive 2TB-mu awet seumur hidup dan tidak membludak berisi sampah ZIP versi lama!
