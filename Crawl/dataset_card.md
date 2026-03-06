---
language:
  - id
task_categories:
  - text-generation
  - question-answering
size_categories:
  - n<1K
license: cc-by-nc-4.0
tags:
  - kemiskinan
  - bansos
  - jawa-timur
  - LLM
  - social-welfare
  - indonesia
---

# 📊 Dataset Card — AITF Poverty & Bansos East Java Corpus

## Dataset Summary

Dataset teks berbahasa Indonesia yang dikumpulkan melalui **web crawling otomatis** untuk keperluan **pre-training / continual pre-training (CPT)** Large Language Model (LLM) yang berspesialisasi pada domain kemiskinan dan bantuan sosial di Provinsi Jawa Timur.

> Dataset ini digunakan sebagai corpus domain-specific untuk melatih LLM agar mampu melakukan klasifikasi dan reasoning terkait program bantuan langsung tunai (BLT), PKH, BPNT, dan pengentasan kemiskinan ekstrem di Jawa Timur.

---

## Dataset Details

| Atribut | Detail |
|---|---|
| **Nama** | AITF Poverty & Bansos East Java Corpus |
| **Versi** | v1.0 (Maret 2026) |
| **Jumlah dokumen** | 163 dokumen |
| **Ukuran file** | ~6.5 MB (JSONL) |
| **Bahasa** | Bahasa Indonesia (`id`) |
| **Format** | JSONL (`data_training_cpt.jsonl`) |
| **Lisensi** | CC BY-NC 4.0 |

---

## Data Collection

### Metode Pengumpulan
Data dikumpulkan menggunakan **custom web crawler** (`WebCrawlerAI`) berbasis Python dengan pendekatan:

1. **Search Engine**: [DuckDuckGo](https://duckduckgo.com) via library `duckduckgo-search`
   - Region: `id-id` (khusus Indonesia)
   - Max results: 15 URL per query
   - Safe search: off (untuk jangkauan lebih luas)

2. **Keyword-driven crawling**: 139 query terstruktur dalam 7 kategori:
   - Definisi & konsep kemiskinan
   - Statistik & data BPS Jawa Timur
   - Topologi & geografi Jawa Timur
   - Kemiskinan per wilayah (38 kab/kota)
   - Pekerjaan & mata pencaharian
   - Program sosial & bansos (PKH, BPNT, BLT, DTKS)
   - Kondisi rentan & kelompok khusus
   - Jurnal & literatur akademik

3. **Sumber konten**: HTML webpage + PDF dokumen

---

## Data Schema

Setiap baris dalam file JSONL memiliki format:

```json
{
  "text": "Judul: [judul halaman]\nIsi: [konten teks]",
  "source_type": "government | academic | news",
  "url": "https://..."
}
```

---

## Source Types

| Tipe | Contoh Domain | Proporsi (estimasi) |
|---|---|---|
| 🏛️ **Government** | `bps.go.id`, `kemensos.go.id`, `dinsos.jatimprov.go.id`, `tnp2k.go.id` | ~30% |
| 🎓 **Academic** | `ejournal.unair.ac.id`, `journal.ugm.ac.id`, `repository.ub.ac.id` | ~35% |
| 📰 **News** | `jatim.antaranews.com`, `beritajatim.com`, `radarsurabaya.jawapos.com` | ~35% |

---

## Filtering & Quality Control

### Filter Relevansi Dua Tingkat

**Tahap 1 — CORE keywords** (wajib ada):
`miskin`, `kemiskinan`, `poverty`, `BLT`, `bansos`, `bantuan langsung tunai`, `penerima bantuan`, `PKH`, `DTKS`, `desil`, `KIP`, `BPNT`, `rentan`, `marjinal`, `subsidi`, `graduasi`

**Tahap 2 — CONTEXT keywords** (wajib ada, kecuali domain prioritas):
`jatim`, `jawa timur` + 38 nama kabupaten/kota Jawa Timur (Surabaya, Malang, Sampang, Bondowoso, dst.)

> **Domain prioritas** (BPS, Kemensos, jurnal akademik) → cukup memenuhi Tahap 1 saja.

### Quality Scoring (0–100)
| Komponen | Max Poin |
|---|---|
| Panjang teks (per 100 karakter) | 40 |
| Kepadatan keyword CORE | 30 |
| Bonus domain: Government | 30 |
| Bonus domain: Academic | 25 |
| Bonus domain: News | 10 |

### Anti-Duplikasi
- **URL-level**: `visited_urls.txt` persisten antar-run
- **Content-level**: MD5 hash dari teks konten

---

## Limitations

- **Tidak mencakup seluruh Jawa Timur secara merata** — beberapa kabupaten mungkin kurang terwakili tergantung hasil search DuckDuckGo.
- **Beberapa dokumen lolos filter** meski kurang relevan (misal: artikel wisata yang menyebut nama kab/kota Jatim).
- **Data dinamis**: konten web bisa berubah; crawl dilakukan Februari–Maret 2026.
- **Bahasa Indonesia dominan**, sangat sedikit campuran bahasa daerah atau Inggris.

---

## Citation

```bibtex
@dataset{aitf_poverty_jatim_2026,
  title     = {AITF Poverty & Bansos East Java Corpus},
  author    = {Alvin},
  year      = {2026},
  month     = {March},
  version   = {1.0},
  language  = {Indonesian},
  note      = {Web-crawled domain-specific corpus for LLM continual pre-training}
}
```
