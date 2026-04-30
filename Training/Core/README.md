#  Core Training Pipeline (Continual Pre-Training)

Folder ini berisi skrip utama untuk melakukan **Continual Pre-Training (CPT)** pada model bahasa (LLM) Qwen3-8B menggunakan library optimasi **Unsloth**. 

##  Kenapa Ada Dua Versi Skrip?

Anda akan menemukan dua file utama untuk proses training:
1. `Train_Qwen3_8B.ipynb` (Jupyter Notebook)
2. `training_server.py` (Python Script)

**Mengapa dipisah?**
- **Versi `.ipynb`** dirancang khusus untuk proses eksperimen, eksplorasi, dan *debugging* interaktif (biasanya dijalankan di Google Colab atau Jupyter lokal). Skrip ini memuat integrasi *mounting* Google Drive otomatis dan memiliki visualisasi matplotlib bawaan di akhir sel.
- **Versi `.py` (`training_server.py`)** merupakan **kembaran identik** dari versi notebook, tetapi dirancang untuk dijalankan di **Server/VPS secara headless** melalui terminal (misalnya di-run dengan `tmux` atau `nohup`). Skrip ini lebih bersih dari kode visualisasi interaktif dan disesuaikan alur path-nya dengan sistem operasi Linux server.

Keduanya memiliki **Logika Inti (Data Processing & Model Configuration) yang 100% SAMA**.

---

##  Penjelasan Detail: `Train_Qwen3_8B.ipynb`

Notebook ini merupakan *core engine* dari pipeline training model kita. Berikut adalah rincian cara kerjanya secara bertahap:

### 1. Persiapan Data (Anti-Catastrophic Forgetting)
- Mengambil dataset crawling spesifik domain dari Hugging Face Hub.
- Melakukan pembersihan data (membuang baris kosong/null).
- **Strategi Penting:** Mencampurkan **20% data dari Wikipedia Indonesia**. Tujuannya agar model tidak mengalami *Catastrophic Forgetting* (lupa kemampuan bahasa umum akibat terlalu difokuskan ke satu domain spesifik).
- Data lalu dipecah (split) menjadi proporsi **90% Train, 5% Validation, dan 5% Test**.

### 2. Pemuatan Model & Quantization (Unsloth)
Pipeline ini sangat bergantung pada **Unsloth** (`FastLanguageModel`) yang mampu mempercepat proses *training* dan memotong penggunaan VRAM secara signifikan.
- **Base Model:** Menggunakan `Qwen/Qwen3-8B-Base`.
- **Kapasitas Konteks:** `max_seq_length` diset pada 4096 token.
- **4-bit Quantization:** Model di-load menggunakan konfigurasi `load_in_4bit = True`. Artinya, beban VRAM yang tadinya butuh belasan GB untuk model 8B dapat ditekan menjadi jauh lebih kecil, sehingga sangat ramah GPU.

### 3. Konfigurasi LoRA (Low-Rank Adaptation)
Alih-alih melatih miliaran parameter dari nol, kita menggunakan teknik parameter-efficient fine-tuning (PEFT):
- **Target Modul:** Menargetkan layer attention & MLP secara komprehensif (`q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`).
- **Rank & Alpha:** Menggunakan `r = 16` dan `lora_alpha = 32`.
- **Dropout:** Diset pada `0.05` untuk mencegah *overfitting*.
- **Gradient Checkpointing:** Diset pada `"unsloth"` yang memberikan optimasi komputasi khusus untuk context length panjang.

### 4. Parameter Training (Hyperparameters)
Berikut adalah konfigurasi parameter utama yang digunakan di dalam `TrainingArguments` untuk menjamin stabilitas dan konvergensi model:
- **`num_train_epochs` = 1** : Karena ini fase CPT (Continual Pre-Training) dan bukan SFT biasa, 1 siklus epoch sudah cukup untuk membuat model mengenali domain baru tanpa merusak pengetahuannya yang lama.
- **`per_device_train_batch_size` = 8** & **`gradient_accumulation_steps` = 16** : Konfigurasi ini menghasilkan *effective batch size* sebesar **128** (8 * 16). Ini sangat penting agar proses update gradient stabil, walau dijalankan pada VRAM yang terbatas.
- **`learning_rate` = 2e-4** : Nilai *learning rate* yang standar dan ideal untuk fine-tuning dengan LoRA.
- **`lr_scheduler_type` = "cosine"** & **`warmup_steps` = 10** : Menggunakan pola kurva *cosine* yang naik perlahan di awal (warmup) lalu turun bertahap. Sangat baik untuk LLM agar tidak kaget di awal training.
- **`bf16` = True** : Menggunakan presisi *bfloat16* (bukan *fp16*) yang mana jauh lebih stabil untuk mencegah nilai loss membeludak (NaN) saat training model berukuran miliar parameter.
- **`weight_decay` = 0.01** : Mencegah *overfitting*.

### 5. Pelatihan & Pemantauan (Monitoring)
- **Tokenisasi Cerdas:** Menambahkan token `<|endoftext|>` (EOS token) di tiap akhir dokumen secara otomatis agar model tahu di mana sebuah dokumen berakhir.
- **WandB Integration:** Menyertakan *Custom Callback* (`WandBPerplexityCallback`) untuk merekam dan menghitung eksponensial dari nilai *Loss* menjadi **Perplexity (PPL)**, yang kemudian dikirim dan divisualisasikan ke *dashboard* Weights & Biases (WandB) secara real-time.

### 6. Penggabungan & Publikasi (Merge & Push)
Di akhir proses *training*, model tidak dibiarkan sebagai *LoRA adapter* yang terpisah. 
Notebook secara otomatis:
- Menyatukan bobot LoRA ke *Base Model* dalam format `16-bit` presisi tinggi.
- Menyimpannya ke folder lokal.
- Mengunggahnya ke repositori Hugging Face (opsional) agar siap digunakan dalam mode *inference*.
