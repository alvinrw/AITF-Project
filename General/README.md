# Testing Score & Evaluasi Model (PPL)

Folder ini berisi kumpulan script yang dirancang untuk melakukan pengujian, evaluasi, dan penggabungan (merging) model LLM (Large Language Model) hasil proses Continual Pre-Training (CPT). 

Secara khusus, script di sini digunakan untuk mengukur metrik **Perplexity (PPL)** dari berbagai model pada dataset target, yang sangat krusial untuk mendeteksi apakah model hasil training mengalami *catastrophic forgetting* atau justru berhasil beradaptasi dengan domain spesifik.

---

##  Daftar Script & Fungsinya

### 1. `Compare_ppl.py`
Script utama untuk membandingkan perplexity dari beberapa base model sekaligus. 
- **Fungsi:** Menghitung perplexity dari model bawaan (seperti Llama-3-8B, Llama-3.1-8B, Qwen3-8B, Qwen3.5-9B) dan membandingkannya dengan model CPT Anda.
- **Dataset yang diuji:** 5% dari dataset domain `alvinrifky/Crawling-MKN_1` digabungkan dengan sampel dari Wikipedia Indonesia.
- **Visualisasi:** Menghasilkan grafik komparasi berupa gambar (`perplexity_comparison.png`) dan tabel hasil berbentuk file CSV (`perplexity_results.csv`).
- **Pengecekan Otomatis:** Memiliki fitur auto-diagnosis & auto-install untuk environment PyTorch dan Transformers yang bermasalah.

### 2. `Cek_ppl.py`
Fungsinya serupa dengan `Compare_ppl.py`, tetapi biasanya dikonfigurasi untuk mengecek versi iterasi CPT yang berbeda (seperti versi `v2`) atau difokuskan pada pengujian model hasil checkpoint tertentu. Format evaluasi dan auto-fix environment-nya identik.

### 3. `merge_terbaik.py`
Script utilitas menggunakan framework **Unsloth**.
- **Fungsi:** Menggabungkan (*merge*) weights dari Base Model dengan adapter LoRA (Low-Rank Adaptation) dari checkpoint terbaik hasil training Anda.
- **Output:** Menghasilkan model utuh (merged 16-bit) yang siap untuk tahap deployment atau tahap SFT (Supervised Fine-Tuning) selanjutnya.

---

##  Penyesuaian Path
Secara bawaan (*default*), path yang merujuk ke folder model di-set menggunakan _relative path_ agar mudah disesuaikan ketika dijalankan di server maupun lokal. Jika Anda ingin mengevaluasi checkpoint lain, silakan buka file script terkait dan sesuaikan blok konfigurasi berikut:

```python
# Contoh di dalam Compare_ppl.py / Cek_ppl.py
CPT_MODEL_PATH = os.path.abspath("./output/qwen3_cpt_8b_v1_final") 

# Contoh di dalam merge_terbaik.py
CHECKPOINT   = "./checkpoints/qwen3_cpt_8b_v1/checkpoint-700" 
OUTPUT_PATH  = "./output/qwen3_cpt_8b_v1_cp700_merged"
```
*(Ganti string `./output/...` dengan folder tempat model/checkpoint Anda disimpan).*

---

##  Cara Menjalankan

1. **Jalankan script evaluasi perplexity:**
   ```bash
   python Compare_ppl.py
   ```
   *(Jika Anda belum menginstal dependensi yang dibutuhkan, script secara pintar akan mendownload dan menginstalnya untuk Anda).*

2. **Jalankan script merge (jika sudah tahu checkpoint terbaik):**
   ```bash
   python merge_terbaik.py
   ```
   *(Pastikan paket `unsloth` sudah terinstal di environment Anda sebelum menjalankan ini).*

---

## Hasil Evaluasi (Mengapa Memilih Qwen3?)

Berdasarkan pengujian ekstensif menggunakan `Compare_ppl.py` terhadap dataset domain khusus (kemiskinan dan berita Jawa Timur) yang dicampur dengan Wikipedia, berikut adalah rangkuman hasilnya:

| Model | Perplexity (PPL) | Jumlah Teks |
| --- | --- | --- |
| `Qwen/Qwen3.5-9B-Base` | 6.6437 | 8134 |
| `meta-llama/Meta-Llama-3-8B` | 4.6352 | 8134 |
| `meta-llama/Llama-3.1-8B` | 4.5560 | 8134 |
| **`Qwen/Qwen3-8B-Base`** | **3.9926** | **8134** |
| **`alvinrifky/Qwen3-8B-AITF-CPT-v2`** | *(Dalam proses)* | - |

1. **Llama-3-8B & Llama-3.1-8B**: Memiliki nilai *perplexity* di kisaran 4.5 - 4.6. Meskipun pemrosesan lebih cepat, model ini masih kesulitan menangkap nuansa lokal dan terminologi spesifik Jawa Timur tanpa adaptasi tambahan.
2. **Qwen/Qwen3.5-9B-Base**: Hasil yang sangat mengejutkan karena perplexity sangat buruk (6.64) dan waktu pemrosesan sangat lambat, mengindikasikan arsitektur ini kurang cocok untuk format dataset yang ada.
3. **Qwen/Qwen3-8B-Base**: Menunjukkan performa bawaan (*baseline*) yang **paling memuaskan dengan PPL 3.9926**. Arsitektur Qwen3 terbukti jauh lebih unggul dalam memproses bahasa Indonesia lokal dibanding keluarga Llama.

Inilah alasan utama mengapa arsitektur **Qwen3-8B** dipilih sebagai tulang punggung (base model) untuk proyek ini.

---

## Akses Model Final (Domain Kemiskinan)

Jika Anda ingin langsung mencoba atau menggunakan model bahasa yang sudah mahir dan dikhususkan untuk **domain kemiskinan di Jawa Timur**, model hasil CPT tersebut telah dipublikasikan dan dapat diakses di Hugging Face Hub:

👉 **[alvinrifky/Qwen3-8B-AITF-CPT-v2](https://huggingface.co/alvinrifky/Qwen3-8B-AITF-CPT-v2)**

Model di atas adalah model *merged* (16-bit) yang sudah siap untuk ditarik menggunakan `AutoModelForCausalLM.from_pretrained()` dan dapat digunakan langsung untuk *inference* atau dilatih lebih lanjut pada tahap SFT.
