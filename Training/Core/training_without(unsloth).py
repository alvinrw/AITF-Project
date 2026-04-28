"""
=======================================================================
  QWEN CPT (Continued Pre-Training) — FULL SCRIPT TANPA UNSLOTH
=======================================================================

Struktur file ini:
  BAGIAN 0 : Import & konstanta
  BAGIAN 1 : Load tokenizer + setup EOS/PAD token
  BAGIAN 2 : Load & preprocessing dataset
  BAGIAN 3 : Tokenisasi + packing dokumen
  BAGIAN 4 : Load model + setup embedding
  BAGIAN 5 : Konfigurasi LoRA
  BAGIAN 6 : Training arguments
  BAGIAN 7 : Data collator
  BAGIAN 8 : Custom Trainer (label masking lintas dokumen)
  BAGIAN 9 : Jalankan training
  BAGIAN 10: Simpan & merge LoRA weights

Requirement:
  pip install transformers==4.44.0 peft==0.12.0 accelerate==0.33.0 \
              datasets trl bitsandbytes wandb

Jalankan:
  # Single GPU
  python qwen_cpt_train.py

  # Multi GPU (pakai accelerate)
  accelerate launch --num_processes 4 qwen_cpt_train.py

  # Dengan DeepSpeed ZeRO-2
  accelerate launch --config_file ds_zero2.yaml qwen_cpt_train.py
=======================================================================
"""

# ======================================================================
# BAGIAN 0: IMPORT & KONSTANTA
# ======================================================================
# Semua library yang dibutuhkan dikumpulkan di sini.
# transformers  : load model & tokenizer HuggingFace
# peft          : LoRA / QLoRA adapter
# datasets      : load & proses dataset
# trl           : SFTTrainer (juga bisa untuk CPT)
# accelerate    : distribusi multi-GPU
# bitsandbytes  : quantization 4-bit (QLoRA)
# ======================================================================

import os
import math
import torch
import wandb
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig,
    set_seed,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)
from datasets import load_dataset, Dataset, concatenate_datasets

# ─── Seed untuk reproducibility ───────────────────────────────────────
set_seed(42)

# ─── Konstanta utama — ubah sesuai kebutuhanmu ────────────────────────
HOME              = os.path.expanduser("~")
MODEL_NAME        = "Qwen/Qwen2.5-0.5B"         # Base model dari HuggingFace
OUTPUT_DIR        = os.path.join(HOME, "Testing_0_5B", "output", "qwen2_5_0_5b_cpt") # Tempat simpan checkpoint
DATA_PATH         = os.path.join(HOME, "Testing", "Data", "data_training_mixed.jsonl") # Path dataset kamu (format jsonl)
TEXT_COLUMN       = "text"                      # Nama kolom teks di dataset
MAX_SEQ_LEN       = 2048                        # Context length saat packing
USE_QLORA         = True                        # True=QLoRA (hemat VRAM), False=LoRA biasa
USE_WANDB         = True                        # Log ke WandB
WANDB_PROJECT     = "AITF - CPT"
RUN_NAME          = "Qwen2.5-0.5B-AITF-CPT_scraped-v1"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ======================================================================
# BAGIAN 1: LOAD TOKENIZER + SETUP EOS & PAD TOKEN
# ======================================================================
# Ini salah satu bagian paling kritis di CPT.
#
# Kenapa EOS penting?
# Saat kita "packing" banyak dokumen pendek jadi satu sequence panjang,
# model harus tahu BATAS antar dokumen. Caranya: tambahkan EOS di akhir
# tiap dokumen sebelum digabung.
#
# Qwen2/2.5 token khusus:
#   <|im_start|>  = 151644  (awal pesan, dipakai di chat template)
#   <|im_end|>    = 151645  (akhir pesan — ini EOS Qwen)
#   <|endoftext|> = 151643  (EOT, dipakai di generasi)
#
# Untuk CPT kita pakai <|endoftext|> sebagai pemisah dokumen,
# karena <|im_end|> lebih relevan untuk format chat.
#
# Kenapa pad_token harus diset?
# Kalau pad_token tidak di-set, HuggingFace akan error saat batching.
# Untuk Qwen, biasanya pad_token = eos_token sudah cukup untuk CPT
# (karena loss pada padding di-mask dengan -100 oleh data collator).
# ======================================================================

print("=" * 60)
print("BAGIAN 1: Load Tokenizer")
print("=" * 60)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,   # Qwen butuh ini karena pakai custom code
    use_fast=True,            # Pakai fast tokenizer (Rust-based, lebih cepat)
)

# ─── Cek token-token penting ──────────────────────────────────────────
print(f"[Tokenizer] vocab size     : {len(tokenizer)}")
print(f"[Tokenizer] eos_token      : {tokenizer.eos_token!r}  (id={tokenizer.eos_token_id})")
print(f"[Tokenizer] bos_token      : {tokenizer.bos_token!r}  (id={tokenizer.bos_token_id})")
print(f"[Tokenizer] pad_token      : {tokenizer.pad_token!r}  (id={tokenizer.pad_token_id})")
print(f"[Tokenizer] unk_token      : {tokenizer.unk_token!r}")

# ─── Qwen2.5 tidak punya pad_token bawaan — harus kita set manual ─────
# Opsi 1: Pakai EOS sebagai PAD (paling umum, simple)
# Opsi 2: Tambah token <|pad|> baru ke vocab (lebih clean tapi butuh
#          resize_token_embeddings dan cost VRAM lebih)
# Untuk CPT: Opsi 1 sudah cukup.
if tokenizer.pad_token is None:
    tokenizer.pad_token    = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id
    print(f"[Tokenizer] pad_token di-set ke eos_token: {tokenizer.pad_token!r}")

# ─── Token pemisah dokumen untuk packing ──────────────────────────────
# Kita pakai <|endoftext|> sebagai separator antar dokumen di dalam
# satu packed sequence. Ini standar untuk CPT.
# Kalau tidak ada, fallback ke eos_token.
if tokenizer.convert_tokens_to_ids("<|endoftext|>") != tokenizer.unk_token_id:
    DOC_SEPARATOR_ID = tokenizer.convert_tokens_to_ids("<|endoftext|>")
else:
    DOC_SEPARATOR_ID = tokenizer.eos_token_id

print(f"[Tokenizer] doc separator  : id={DOC_SEPARATOR_ID}")


# ======================================================================
# BAGIAN 2: LOAD DATASET
# ======================================================================
# Format dataset yang diharapkan:
#   JSONL — tiap baris adalah satu dokumen:
#   {"text": "Ini adalah dokumen pertama tentang ..."}
#   {"text": "Dokumen kedua membahas ..."}
#
# Kalau datamu dari HuggingFace Hub, ganti dengan:
#   dataset = load_dataset("nama/dataset", split="train")
#
# Tips kualitas data:
#   - Minimal 100MB teks untuk CPT yang bermakna
#   - Hapus duplikat sebelum training (MinHash dedup)
#   - Filter dokumen < 50 karakter (terlalu pendek, tidak informatif)
#   - Pastikan encoding UTF-8
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 2: Load Dataset")
print("=" * 60)

# ─── Load dari file lokal ─────────────────────────────────────────────
if os.path.exists(DATA_PATH):
    dataset = load_dataset(
        "json",
        data_files={"train": DATA_PATH},
        split="train",
    )
else:
    # Fallback: pakai dataset dummy untuk testing
    print("[WARNING] DATA_PATH tidak ditemukan, pakai dataset dummy!")
    dummy_texts = [
        "Kecerdasan buatan adalah cabang ilmu komputer yang berfokus pada pembuatan sistem yang dapat melakukan tugas-tugas yang memerlukan kecerdasan manusia.",
        "Pembelajaran mesin adalah subset dari kecerdasan buatan yang memungkinkan komputer belajar dari data tanpa diprogram secara eksplisit.",
        "Model bahasa besar dilatih pada korpus teks yang sangat besar menggunakan arsitektur transformer.",
        "Indonesia adalah negara kepulauan terbesar di dunia dengan lebih dari 17.000 pulau.",
        "Bahasa Python dikenal karena sintaksisnya yang bersih dan mudah dibaca, membuatnya populer untuk pemula dan profesional.",
    ] * 200  # Dikali 200 supaya ada cukup data untuk demo
    dataset = Dataset.from_dict({TEXT_COLUMN: dummy_texts})

print(f"[Dataset] Jumlah dokumen   : {len(dataset):,}")
print(f"[Dataset] Kolom tersedia   : {dataset.column_names}")

# ─── Filter dokumen terlalu pendek ────────────────────────────────────
dataset = dataset.filter(
    lambda x: len(x[TEXT_COLUMN]) >= 50,
    desc="Filter dokumen pendek"
)
print(f"[Dataset] Setelah filter   : {len(dataset):,} dokumen")

# ─── Split train / validation ─────────────────────────────────────────
split = dataset.train_test_split(test_size=0.005, seed=42)  # 0.5% untuk eval
train_dataset = split["train"]
eval_dataset  = split["test"]
print(f"[Dataset] Train            : {len(train_dataset):,}")
print(f"[Dataset] Eval             : {len(eval_dataset):,}")


# ======================================================================
# BAGIAN 3: TOKENISASI + PACKING DOKUMEN
# ======================================================================
# Packing = menggabungkan banyak dokumen pendek jadi satu sequence
# sepanjang MAX_SEQ_LEN. Ini meningkatkan efisiensi GPU secara drastis
# karena tidak ada padding yang terbuang.
#
# Contoh ilustrasi packing (MAX_SEQ_LEN = 10):
#
#   Dokumen A: [tok1, tok2, tok3, EOS]
#   Dokumen B: [tok4, tok5, EOS]
#   Dokumen C: [tok6, tok7, tok8, tok9, EOS]
#
#   Hasil packing:
#   Chunk 1:  [tok1, tok2, tok3, EOS, tok4, tok5, EOS, tok6, tok7, tok8]
#   Chunk 2:  [tok9, EOS]
#
# PENTING: Loss dihitung untuk SEMUA token, termasuk EOS.
# Model belajar "setelah EOS, konten baru bisa dimulai".
#
# Kenapa tidak pakai padding?
# Padding menghasilkan banyak token -100 (yang di-ignore di loss).
# Ini membuang komputasi GPU. Packing menghilangkan pemborosan ini.
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 3: Tokenisasi + Packing")
print("=" * 60)

def tokenize_and_pack(examples, tokenizer, max_len, doc_separator_id):
    """
    Tokenisasi batch dokumen lalu pack jadi chunks berukuran max_len.
    
    Alur:
    1. Tokenisasi tiap dokumen
    2. Tambahkan doc_separator_id (EOS) di akhir tiap dokumen
    3. Gabungkan semua token jadi satu deret panjang
    4. Potong jadi chunks ukuran max_len
    5. Return sebagai dict {"input_ids": [...], "attention_mask": [...]}
    """
    all_token_ids = []
    
    for text in examples[TEXT_COLUMN]:
        # Tokenisasi tanpa special tokens tambahan
        # (kita handle sendiri EOS-nya)
        token_ids = tokenizer.encode(
            text,
            add_special_tokens=False,  # Jangan tambah BOS/EOS otomatis
        )
        # Tambahkan separator di akhir dokumen
        token_ids.append(doc_separator_id)
        all_token_ids.extend(token_ids)
    
    # ─── Potong jadi chunks ───────────────────────────────────────────
    chunks_input_ids      = []
    chunks_attention_mask = []
    
    for i in range(0, len(all_token_ids), max_len):
        chunk = all_token_ids[i : i + max_len]
        
        # Buang chunk terakhir kalau terlalu pendek (< 50% max_len)
        # supaya tidak ada chunk nanggung yang merusak training
        if len(chunk) < max_len // 2:
            break
        
        # Pad chunk kalau lebih pendek dari max_len
        # (hanya terjadi di chunk terakhir yang tidak dibuang)
        pad_len = max_len - len(chunk)
        attention_mask = [1] * len(chunk) + [0] * pad_len
        chunk = chunk + [tokenizer.pad_token_id] * pad_len
        
        chunks_input_ids.append(chunk)
        chunks_attention_mask.append(attention_mask)
    
    return {
        "input_ids":      chunks_input_ids,
        "attention_mask": chunks_attention_mask,
    }


# ─── Terapkan ke dataset ──────────────────────────────────────────────
# batched=True supaya pemrosesan lebih cepat
# remove_columns untuk hapus kolom teks asli (sudah tidak dibutuhkan)
tokenize_fn = lambda x: tokenize_and_pack(x, tokenizer, MAX_SEQ_LEN, DOC_SEPARATOR_ID)

tokenized_train = train_dataset.map(
    tokenize_fn,
    batched=True,
    batch_size=1000,
    remove_columns=train_dataset.column_names,
    desc="Tokenisasi + packing train",
    num_proc=4,   # Paralel 4 CPU — sesuaikan dengan jumlah core
)

tokenized_eval = eval_dataset.map(
    tokenize_fn,
    batched=True,
    batch_size=1000,
    remove_columns=eval_dataset.column_names,
    desc="Tokenisasi + packing eval",
    num_proc=4,
)

print(f"[Tokenized] Train chunks   : {len(tokenized_train):,}")
print(f"[Tokenized] Eval chunks    : {len(tokenized_eval):,}")
print(f"[Tokenized] Estimasi total tokens train : {len(tokenized_train) * MAX_SEQ_LEN:,}")

# Verifikasi bentuk data
sample = tokenized_train[0]
print(f"[Tokenized] Shape sample   : input_ids={len(sample['input_ids'])}, mask={len(sample['attention_mask'])}")


# ======================================================================
# BAGIAN 4: LOAD MODEL + SETUP EMBEDDING
# ======================================================================
# Ada dua mode loading:
#
# A) QLoRA (USE_QLORA=True):
#    Model di-load dalam presisi 4-bit (NF4 quantization).
#    Menghemat ~75% VRAM. Qwen2.5-7B butuh ~5GB VRAM (vs ~16GB bf16).
#    Lalu LoRA adapter di-attach di atas model 4-bit.
#
# B) LoRA biasa (USE_QLORA=False):
#    Model di-load dalam bfloat16.
#    Lebih cepat dan akurat, tapi butuh lebih banyak VRAM.
#
# Tentang bfloat16 vs float16:
#    bfloat16 lebih stabil untuk training (range eksponent lebih lebar).
#    float16 lebih presisi tapi lebih rentan NaN/overflow.
#    Untuk training di GPU Ampere ke atas (A100, 3090, 4090), pakai bf16.
#
# Tentang flash_attention_2:
#    Implementasi attention yang jauh lebih efisien memori & kecepatan.
#    Wajib dipakai kalau GPU support (Ampere+). Untuk GPU lama (V100,
#    RTX 20xx), ganti dengan "eager" atau hapus param ini.
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 4: Load Model")
print("=" * 60)

# ─── Konfigurasi quantization untuk QLoRA ─────────────────────────────
bnb_config = None
if USE_QLORA:
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",          # NF4 lebih bagus dari fp4 untuk LLM
        bnb_4bit_compute_dtype=torch.bfloat16,  # Komputasi tetap bf16
        bnb_4bit_use_double_quant=True,     # Double quantization hemat VRAM lagi
    )
    print("[Model] Mode: QLoRA (4-bit NF4)")
else:
    print("[Model] Mode: LoRA biasa (bfloat16)")

# ─── Load model ───────────────────────────────────────────────────────
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,          # None kalau tidak QLoRA
    torch_dtype=torch.bfloat16,
    device_map="auto",                       # Otomatis distribusi ke GPU/CPU
    trust_remote_code=True,
    attn_implementation="flash_attention_2", # Ganti "eager" kalau tidak support
)

print(f"[Model] Loaded: {MODEL_NAME}")
print(f"[Model] dtype  : {model.dtype}")
print(f"[Model] device : {model.device}")

# ─── Cek ukuran embedding vs vocab tokenizer ──────────────────────────
# Kalau ada mismatch, WAJIB resize.
# Ini bisa terjadi kalau kamu tambah custom token ke tokenizer.
vocab_size_model     = model.get_input_embeddings().weight.shape[0]
vocab_size_tokenizer = len(tokenizer)

print(f"[Embedding] Vocab model     : {vocab_size_model:,}")
print(f"[Embedding] Vocab tokenizer : {vocab_size_tokenizer:,}")

if vocab_size_model != vocab_size_tokenizer:
    print(f"[Embedding] MISMATCH! Resize dari {vocab_size_model} → {vocab_size_tokenizer}")
    model.resize_token_embeddings(vocab_size_tokenizer)
    
    # ─── Inisialisasi token baru dari rata-rata existing embedding ────
    # JANGAN biarkan random! Random embedding bikin training tidak stabil.
    # Cara terbaik: rata-rata dari semua token existing.
    n_new = vocab_size_tokenizer - vocab_size_model
    print(f"[Embedding] Init {n_new} token baru dari mean existing embedding")
    
    with torch.no_grad():
        embed_weight = model.get_input_embeddings().weight
        mean_embed   = embed_weight[:-n_new].mean(dim=0)
        embed_weight[-n_new:] = mean_embed
        
        # Sama untuk lm_head (output embedding)
        lm_head_weight = model.get_output_embeddings().weight
        if lm_head_weight.shape[0] == vocab_size_tokenizer:
            lm_head_mean = lm_head_weight[:-n_new].mean(dim=0)
            lm_head_weight[-n_new:] = lm_head_mean
else:
    print("[Embedding] Vocab size match — tidak perlu resize")

# ─── Persiapkan model untuk kbit training (khusus QLoRA) ──────────────
# Fungsi ini dari PEFT. Kerjanya:
# 1. Cast layer norm ke float32 (supaya stabil)
# 2. Pastikan lm_head dalam float32
# 3. Aktifkan gradient checkpointing
if USE_QLORA:
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
    )
else:
    # Untuk LoRA biasa, aktifkan gradient checkpointing manual
    model.gradient_checkpointing_enable()

# Ini penting untuk gradient checkpointing + LoRA
model.enable_input_require_grads()


# ======================================================================
# BAGIAN 5: KONFIGURASI LORA
# ======================================================================
# LoRA (Low-Rank Adaptation) = freeze semua bobot model asli, lalu
# tambahkan matrix kecil (rank rendah) di sebelah tiap linear layer.
# Hanya matrix kecil ini yang dilatih.
#
# Parameter penting:
#
#   r (rank)        : Dimensi matrix LoRA. Lebih besar = lebih kapasitas
#                     tapi lebih banyak parameter. Untuk CPT: 64-128.
#                     Untuk SFT: 16-64 sudah cukup.
#
#   lora_alpha      : Scaling factor. Biasanya 2x rank.
#                     Learning rate efektif LoRA ≈ lr * (alpha/r).
#
#   target_modules  : Layer mana yang dapat LoRA adapter.
#                     Qwen2 pakai GQA (Grouped Query Attention) dengan
#                     modul q/k/v/o_proj dan FFN gate/up/down_proj.
#                     Untuk CPT: masukkan semua modul supaya maksimal.
#
#   modules_to_save : Layer yang di-copy PENUH dan dilatih (bukan LoRA).
#                     embed_tokens dan lm_head dimasukkan sini kalau kamu
#                     resize vocab atau mau embedding ikut update di CPT.
#
#   lora_dropout    : Dropout pada adapter. 0.05 standard.
#
#   bias            : "none" = bias tidak dilatih (standard untuk CPT).
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 5: Konfigurasi LoRA")
print("=" * 60)

# Cek nama modul yang ada di model (debugging helper)
# Uncomment kalau mau lihat semua nama layer:
# for name, module in model.named_modules():
#     print(name)

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    
    # ─── Rank & scaling ───────────────────────────────────────────────
    r=64,              # Untuk CPT pakai rank lebih tinggi dari SFT
    lora_alpha=128,    # 2x rank adalah aturan praktis yang bagus
    lora_dropout=0.05,
    bias="none",
    
    # ─── Target modules — semua linear layer Qwen2 ────────────────────
    # q_proj, k_proj, v_proj : Query, Key, Value projection di attention
    # o_proj                 : Output projection attention
    # gate_proj, up_proj     : FFN SwiGLU gating
    # down_proj              : FFN projection turun
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    
    # ─── Modules to save ──────────────────────────────────────────────
    # Uncomment baris ini HANYA kalau kamu resize vocab (tambah token baru).
    # Kalau tidak resize, comment saja — hemat memori.
    # modules_to_save=["embed_tokens", "lm_head"],
    
    inference_mode=False,  # False = mode training
)

model = get_peft_model(model, lora_config)

# ─── Laporan parameter ────────────────────────────────────────────────
model.print_trainable_parameters()
# Contoh output:
# trainable params: 167,772,160 || all params: 7,783,800,832 || trainable%: 2.1551


# ======================================================================
# BAGIAN 6: TRAINING ARGUMENTS
# ======================================================================
# Penjelasan tiap parameter penting:
#
#   per_device_train_batch_size :
#     Batch per GPU. Kalau OOM, turunkan ini dulu.
#
#   gradient_accumulation_steps :
#     Akumulasi gradient sebelum update. Effective batch size =
#     batch_size × grad_accum × n_gpu.
#     Contoh: 2 × 8 × 4 GPU = effective batch 64.
#
#   learning_rate :
#     Untuk CPT: 1e-5 sampai 5e-5. Lebih kecil dari SFT (1e-4 ~ 3e-4).
#     CPT butuh learning rate rendah supaya tidak terlalu jauh dari
#     distribusi pretrain asli.
#
#   lr_scheduler_type + warmup_ratio :
#     Cosine decay adalah standar. Warmup 5% dari total steps untuk
#     stabilkan training di awal sebelum learning rate penuh.
#
#   bf16 :
#     Wajib True untuk GPU Ampere+. Lebih stabil dari fp16.
#
#   max_grad_norm :
#     Gradient clipping. Mencegah gradient meledak (exploding gradient).
#     1.0 adalah nilai standar.
#
#   weight_decay :
#     Regularisasi L2. Mencegah overfitting. 0.1 standard untuk LLM.
#
#   save_total_limit :
#     Hanya simpan N checkpoint terakhir. Hemat disk space.
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 6: Training Arguments")
print("=" * 60)

# Setup WandB
if USE_WANDB:
    os.environ['WANDB_API_KEY'] = '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'
    os.environ["WANDB_PROJECT"] = WANDB_PROJECT
    wandb.login()
    wandb.init(project=WANDB_PROJECT, name=RUN_NAME)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    
    # ─── Batch & gradient ─────────────────────────────────────────────
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=8,
    # Effective batch size = 2 × 8 × (jumlah GPU)
    
    # ─── Learning rate & scheduler ────────────────────────────────────
    learning_rate=2e-5,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,        # 5% pertama dari total training steps
    
    # ─── Durasi training ──────────────────────────────────────────────
    num_train_epochs=1,       # CPT biasanya 1-3 epoch
    # Atau pakai max_steps untuk kontrol lebih presisi:
    # max_steps=10000,
    
    # ─── Presisi & optimasi memori ────────────────────────────────────
    bf16=torch.cuda.is_bf16_supported(),
    fp16=not torch.cuda.is_bf16_supported(),
    tf32=True,                # Tensor Float 32 — aktifkan untuk A100
    optim="adamw_torch_fused" if torch.cuda.is_available() else "adamw_torch",
    # adamw_torch_fused lebih efisien memori dan lebih cepat
    
    # ─── Stabilitas ───────────────────────────────────────────────────
    max_grad_norm=1.0,
    weight_decay=0.1,
    
    # ─── Gradient checkpointing ───────────────────────────────────────
    # Menukar waktu komputasi dengan memori. Aktifkan kalau OOM.
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    
    # ─── Evaluasi ─────────────────────────────────────────────────────
    eval_strategy="steps",
    eval_steps=500,
    
    # ─── Logging ──────────────────────────────────────────────────────
    logging_dir=f"{OUTPUT_DIR}/logs",
    logging_steps=10,
    report_to="wandb" if USE_WANDB else "tensorboard",
    run_name=RUN_NAME,
    
    # ─── Saving ───────────────────────────────────────────────────────
    save_strategy="steps",
    save_steps=500,
    save_total_limit=3,       # Simpan 3 checkpoint terakhir
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    
    # ─── DataLoader ───────────────────────────────────────────────────
    dataloader_num_workers=4,
    dataloader_pin_memory=True,
    remove_unused_columns=False,  # PENTING: jangan hapus kolom kita
    
    # ─── Group by length ──────────────────────────────────────────────
    # MATIKAN untuk CPT karena data sudah di-pack uniform panjangnya
    group_by_length=False,
)

print("[Args] Training arguments dikonfigurasi")
print(f"[Args] Output dir: {OUTPUT_DIR}")


# ======================================================================
# BAGIAN 7: DATA COLLATOR
# ======================================================================
# Data collator bertugas mengubah list sampel dari dataset jadi
# satu batch tensor yang siap masuk ke model.
#
# DataCollatorForLanguageModeling dengan mlm=False:
# - Menyusun input_ids dan attention_mask jadi tensor
# - Membuat labels = input_ids (untuk causal LM, prediksi token berikutnya)
# - Mask token padding dengan -100 di labels (diabaikan saat hitung loss)
#
# CATATAN: Labels = -100 berarti loss untuk token itu tidak dihitung.
# Ini penting supaya model tidak belajar memprediksi padding token.
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 7: Data Collator")
print("=" * 60)

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,             # False = Causal LM (prediksi next token)
                           # True  = Masked LM (BERT-style, bukan untuk GPT)
    pad_to_multiple_of=8,  # Pad panjang ke kelipatan 8, efisiensi tensor core
)

print("[Collator] DataCollatorForLanguageModeling (causal LM) siap")


# ======================================================================
# BAGIAN 8: CUSTOM TRAINER
# ======================================================================
# Kita extend Trainer standar untuk dua hal:
#
# 1. Compute metrics — hitung perplexity dari eval loss.
#    Perplexity = exp(loss). Makin rendah makin bagus.
#    Ini metrik utama untuk menilai kualitas CPT.
#
# 2. Label masking lintas dokumen (opsional tapi recommended).
#    Masalah: kalau dokumen A di-pack dengan dokumen B dalam satu
#    sequence, ada risiko model belajar "token terakhir dokumen A
#    → token pertama dokumen B". Ini tidak logis secara linguistik.
#    Solusi: set label token pertama setelah EOS menjadi -100,
#    sehingga loss tidak dihitung untuk transisi antar dokumen.
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 8: Custom Trainer")
print("=" * 60)

class CPTTrainer(Trainer):
    """
    Custom Trainer untuk CPT dengan:
    - Perhitungan perplexity saat evaluasi
    - Label masking lintas dokumen (cross-doc label masking)
    """
    
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        """
        Override compute_loss untuk menerapkan cross-document label masking.
        
        Alur:
        1. Ambil input_ids dari batch
        2. Buat labels = copy input_ids
        3. Temukan posisi EOS (pemisah dokumen)
        4. Set token SETELAH EOS menjadi -100 (diabaikan di loss)
        5. Jalankan forward pass dengan labels yang sudah di-mask
        """
        input_ids = inputs["input_ids"]
        
        # ─── Buat labels dari input_ids ───────────────────────────────
        labels = input_ids.clone()
        
        # ─── Mask padding tokens ──────────────────────────────────────
        # Token padding tidak boleh dihitung dalam loss
        if "attention_mask" in inputs:
            labels[inputs["attention_mask"] == 0] = -100
        
        # ─── Cross-document label masking ─────────────────────────────
        # Cari posisi EOS di tiap sequence dalam batch
        eos_id = DOC_SEPARATOR_ID
        for batch_idx in range(input_ids.shape[0]):
            seq = input_ids[batch_idx]
            eos_positions = (seq == eos_id).nonzero(as_tuple=True)[0]
            for pos in eos_positions:
                next_pos = pos + 1
                if next_pos < len(seq):
                    # Token pertama setelah EOS tidak dihitung dalam loss
                    # (ini adalah awal dokumen baru, bukan lanjutan dokumen sebelumnya)
                    labels[batch_idx, next_pos] = -100
        
        # ─── Forward pass ─────────────────────────────────────────────
        inputs_for_forward = {
            "input_ids":      input_ids,
            "attention_mask": inputs.get("attention_mask"),
            "labels":         labels,
        }
        
        outputs = model(**inputs_for_forward)
        loss    = outputs.loss
        
        return (loss, outputs) if return_outputs else loss
    
    def evaluate(self, *args, **kwargs):
        """
        Override evaluate untuk tambahkan logging perplexity.
        """
        output = super().evaluate(*args, **kwargs)
        
        eval_loss = output.get("eval_loss")
        if eval_loss is not None:
            perplexity = math.exp(eval_loss)
            output["eval_perplexity"] = perplexity
            print(f"\n[Eval] Loss={eval_loss:.4f} | Perplexity={perplexity:.2f}")
            
            if USE_WANDB:
                wandb.log({"eval/perplexity": perplexity})
        
        return output

print("[Trainer] CPTTrainer siap")


# ======================================================================
# BAGIAN 9: INISIALISASI & JALANKAN TRAINING
# ======================================================================
# Di sini semua bagian sebelumnya disatukan dalam satu Trainer object.
# Lalu training dijalankan dengan trainer.train().
#
# Yang terjadi saat training berjalan:
# 1. DataLoader mengambil batch dari tokenized_train
# 2. CPTTrainer.compute_loss dipanggil tiap step
# 3. Forward pass → hitung loss → backward pass → gradient → update
# 4. Tiap logging_steps: print loss ke konsol & WandB
# 5. Tiap eval_steps: evaluasi di tokenized_eval, hitung perplexity
# 6. Tiap save_steps: simpan checkpoint ke output_dir
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 9: Training")
print("=" * 60)

trainer = CPTTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_eval,
    data_collator=data_collator,
    tokenizer=tokenizer,
)

print("[Trainer] Mulai training...")
print(f"[Trainer] Total train samples  : {len(tokenized_train):,}")
print(f"[Trainer] Batch size efektif   : {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")

# ─── Cek apakah ada checkpoint yang bisa di-resume ────────────────────
last_checkpoint = None
if os.path.isdir(OUTPUT_DIR):
    from transformers.trainer_utils import get_last_checkpoint
    last_checkpoint = get_last_checkpoint(OUTPUT_DIR)
    if last_checkpoint:
        print(f"[Trainer] Resume dari checkpoint: {last_checkpoint}")

# ─── Jalankan training ────────────────────────────────────────────────
train_result = trainer.train(resume_from_checkpoint=last_checkpoint)

# ─── Simpan hasil training ────────────────────────────────────────────
trainer.save_state()
trainer.log_metrics("train", train_result.metrics)
trainer.save_metrics("train", train_result.metrics)

print(f"\n[Training] Selesai!")
print(f"[Training] Total steps     : {train_result.global_step}")
print(f"[Training] Train loss akhir: {train_result.metrics.get('train_loss', 'N/A'):.4f}")


# ======================================================================
# BAGIAN 10: SIMPAN & MERGE LORA WEIGHTS
# ======================================================================
# Setelah training, kita punya dua opsi penyimpanan:
#
# A) Simpan LoRA adapter saja (file kecil, ~300MB untuk r=64):
#    Cocok kalau mau lanjut fine-tuning lagi, atau mau share adapter.
#    Load nanti: model = PeftModel.from_pretrained(base_model, adapter_path)
#
# B) Merge LoRA ke base model lalu simpan model utuh:
#    Cocok untuk deployment. Model bisa di-load langsung tanpa PEFT.
#    Ukuran file = ukuran model full (misal ~14GB untuk Qwen2.5-7B bf16).
#
# Rekomendasi:
#    Simpan adapter dulu (A), lalu merge untuk deployment (B).
# ======================================================================

print("\n" + "=" * 60)
print("BAGIAN 10: Simpan & Merge LoRA")
print("=" * 60)

# ─── A: Simpan LoRA adapter ───────────────────────────────────────────
adapter_save_path = f"{OUTPUT_DIR}/lora-adapter"
model.save_pretrained(adapter_save_path)
tokenizer.save_pretrained(adapter_save_path)
print(f"[Save] LoRA adapter disimpan ke: {adapter_save_path}")

# ─── B: Merge LoRA ke base model ──────────────────────────────────────
print("[Merge] Merging LoRA weights ke base model...")

# Load ulang dalam presisi penuh untuk merge
from peft import PeftModel

base_model_for_merge = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="cpu",           # Load ke CPU untuk merge supaya hemat VRAM
    trust_remote_code=True,
)

# Attach dan merge adapter
merged_model = PeftModel.from_pretrained(
    base_model_for_merge,
    adapter_save_path,
)
merged_model = merged_model.merge_and_unload()  # Merge LoRA → hapus adapter

# Simpan model yang sudah di-merge
merged_save_path = f"{OUTPUT_DIR}/merged-model"
merged_model.save_pretrained(
    merged_save_path,
    safe_serialization=True,     # Simpan dalam format safetensors (lebih aman)
    max_shard_size="4GB",        # Split jadi file-file 4GB supaya mudah dikelola
)
tokenizer.save_pretrained(merged_save_path)

print(f"[Merge] Model merged disimpan ke: {merged_save_path}")
print("\n[DONE] CPT selesai! Model siap dipakai atau dilanjutkan ke SFT.")

if USE_WANDB:
    wandb.finish()

# ======================================================================
# QUICK TEST — verifikasi model hasil CPT bisa generate teks
# ======================================================================
print("\n" + "=" * 60)
print("QUICK TEST: Generate teks dari model hasil CPT")
print("=" * 60)

from transformers import pipeline

pipe = pipeline(
    "text-generation",
    model=merged_save_path,
    tokenizer=merged_save_path,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

test_prompt = "Kecerdasan buatan adalah"
output = pipe(
    test_prompt,
    max_new_tokens=100,
    do_sample=True,
    temperature=0.7,
    top_p=0.9,
    repetition_penalty=1.1,
)

print(f"[Test] Prompt  : {test_prompt}")
print(f"[Test] Output  : {output[0]['generated_text']}")
print("\nCPT pipeline selesai!")