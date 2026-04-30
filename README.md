# AITF - Domain-Specific Language Model Pipeline (Kemiskinan Jawa Timur)

Repositori ini memuat *pipeline* lengkap (dari hulu ke hilir) untuk merancang, melatih, dan mengevaluasi *Large Language Model* (LLM) yang sangat terspesialisasi pada pemahaman konteks dan terminologi lokal di Indonesia.

##  Usecase Utama
Proyek ini berfokus pada **Domain Kemiskinan di Jawa Timur**. 
Model bahasa umum (*General LLMs*) sering kali kesulitan memahami struktur berita lokal, kebijakan pemerintah daerah, maupun dialek dan terminologi spesifik mengenai kemiskinan di tingkat provinsi (misalnya sebutan program dinas, statistik lokal, hingga kondisi sosial demografis wilayah).

Oleh karena itu, tujuan repositori ini adalah melakukan tahapan **Continual Pre-Training (CPT)** menggunakan data asli hasil *crawling* dari portal-portal berita Jawa Timur (seperti Antara Jatim, Malang Times, Berita Jatim, dll.) agar model mendapatkan intuisi linguistik yang tajam mengenai topik ini, tanpa melupakan pengetahuan dasar bahasanya (*catastrophic forgetting*).

---

##  Struktur Repositori

Repositori ini dibagi menjadi 3 pilar kerja utama (masing-masing direktori memiliki file `README.md` tersendiri untuk penjelasan mendalam):

### 1. `Crawl/` (Pengumpulan Data)
Pusat *pipeline* ekstraksi (*scraper* dan *crawler*). Di sinilah kita mencari target URL secara spesifik dengan teknik **Google Dorks**, melakukan ekstraksi artikel tanpa noise dari portal berita menggunakan *CSS Selectors*, menarik teks dari dokumen resmi PDF, dan memformat semuanya menjadi dataset JSONL bersih siap training.

### 2. `Training/` (Pelatihan Model)
Jantung dari proses CPT. Di sinilah *base model* diajarkan "bahasa lokal Jawa Timur" secara intensif menggunakan metode kuantisasi 4-bit dan library optimasi **Unsloth**. Pipeline mencampur data domain kemiskinan dengan 20% data Wikipedia sebagai penyeimbang bobot general.

### 3. `General/` (Evaluasi & Utilitas)
Folder utilitas diagnostik untuk mengecek kualitas model pasca (dan pra) training. Berisi sistem untuk melakukan **pengujian Perplexity (PPL)**, membandingkan performa antara beberapa model, serta *script* untuk menyatukan kembali (*merge*) adapter LoRA ke *base model* utuh (16-bit).

---

##  Mengapa Memilih Qwen3-8B?

Sebelum mengeksekusi tahapan panjang *Continual Pre-Training*, kami melakukan uji coba ekstensif *(benchmarking)* menggunakan script `Compare_ppl.py` terhadap berbagai arsitektur base model terkenal (Llama-3, Llama-3.1, Qwen3.5-9B, dan Qwen3-8B).

Pengujian ini menggunakan lebih dari 8.134 teks artikel dan dokumen terkait Jawa Timur. Hasilnya sangat krusial dalam pengambilan keputusan proyek ini:

1. **Kelemahan Keluarga Llama:** Base model barat seperti Llama-3-8B maupun Llama-3.1-8B memiliki *perplexity* (PPL) yang agak tinggi, tertahan di kisaran **4.5 - 4.6**. Llama memang hebat untuk bahasa Inggris, namun kurang lincah dalam menangkap sintaksis murni bahasa lokal tanpa instruksi berlapis.
2. **Keunggulan Qwen3-8B:** Mengejutkannya, **`Qwen/Qwen3-8B-Base`** menang telak di pengujian ini dengan mencetak PPL terendah di angka **3.9926**. Qwen secara desain arsitektur terbukti jauh lebih peka dan tangguh terhadap serapan kosakata Asia/Austronesia, termasuk bahasa Indonesia ragam jurnalistik lokal.
3. **Anomali Skala:** Pengujian juga menunjukkan bahwa menggunakan model yang sedikit lebih besar seperti *Qwen3.5-9B* justru memberikan hasil sangat buruk (PPL meroket ke angka 6.64).

Berdasarkan rasional empiris dan hitung-hitungan *loss* inilah, **Qwen3-8B** dinobatkan sebagai *backbone* utama yang paling layak dilatih untuk membedah data Jatim.

---

##  Model Final 
Bagi Anda yang ingin menggunakan hasil akhir dari seluruh rangkaian pipeline ini, model yang telah mahir dan di-CPT khusus untuk domain kemiskinan sudah diunggah dan bisa ditarik langsung lewat Hugging Face:

**[alvinrifky/Qwen3-8B-AITF-CPT-v2](https://huggingface.co/alvinrifky/Qwen3-8B-AITF-CPT-v2)**
