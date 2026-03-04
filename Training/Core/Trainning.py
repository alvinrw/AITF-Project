# ==========================================
# TRAINING PIPELINE SFT - POVERTY MODEL-1
# ==========================================
# Framework  : Unsloth & TRL
# Base Model : Qwen2.5-7B-Instruct
# Technique  : QLoRA (4-bit)
# Dataset    : <isi DATASET_NAME di bawah>
# ==========================================

import os
import json
import torch
import pandas as pd
from tqdm import tqdm
from pathlib import Path

# ── Path konfigurasi ──────────────────────────────────────────────────────────
BASE_DIR      = Path("/home/user/project_ai")
DATASET_DIR   = BASE_DIR / "dataset"

# ↓↓↓ ISI NAMA FILE DATASET KAMU DI SINI (tanpa ekstensi) ↓↓↓
DATASET_NAME  = "GANTI_NAMA_DATASET_KAMU"          # contoh: "data_poverty_v2"
# ↑↑↑ ─────────────────────────────────────────────────────── ↑↑↑

RAW_FILE      = DATASET_DIR / f"{DATASET_NAME}.jsonl"
CLEANED_FILE  = DATASET_DIR / f"{DATASET_NAME}_validated.jsonl"
OUTPUT_MODEL  = BASE_DIR   / "outputs" / f"{DATASET_NAME}_lora"
TRAIN_OUTPUT  = BASE_DIR   / "outputs" / f"{DATASET_NAME}_training_runs"

OUTPUT_MODEL.mkdir(parents=True, exist_ok=True)
TRAIN_OUTPUT.mkdir(parents=True, exist_ok=True)

# =============================================================================
# STEP 1 – VALIDASI & BERSIHKAN DATASET
# =============================================================================
print("=" * 60)
print(f"[STEP 1] Validasi dataset: {RAW_FILE.name}")
print("=" * 60)

bad_lines   = 0
good_lines  = 0

with open(RAW_FILE, "r", encoding="utf-8") as f_in, \
     open(CLEANED_FILE, "w", encoding="utf-8") as f_out:

    for i, line in enumerate(f_in):
        line = line.strip()
        if not line:          # skip baris kosong
            continue
        try:
            obj = json.loads(line)

            # --- validasi struktur minimal: harus punya key "messages" -------
            if "messages" not in obj:
                raise ValueError("Key 'messages' tidak ditemukan")

            # --- validasi isi messages: minimal 2 turn (system/user + asisten)
            msgs = obj["messages"]
            if len(msgs) < 2:
                raise ValueError(f"Jumlah messages kurang: {len(msgs)}")

            f_out.write(line + "\n")
            good_lines += 1

        except Exception as e:
            print(f"  ⚠ Melewati baris {i + 1}: {e}")
            bad_lines += 1

print(f"\n  ✓ Baris valid   : {good_lines:,}")
print(f"  ✗ Baris dibuang : {bad_lines:,}")
print(f"  → File bersih   : {CLEANED_FILE}\n")


# =============================================================================
# STEP 2 – INSTALL DEPENDENSI  (jalankan sekali di environment baru)
# =============================================================================
# Uncomment baris di bawah jika belum ter-install:
# import subprocess, sys
# subprocess.run([sys.executable, "-m", "pip", "install", "unsloth"], check=True)
# subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps",
#                 "trl<0.9.0", "peft", "accelerate", "bitsandbytes"], check=True)


# =============================================================================
# STEP 3 – LOAD MODEL & TOKENIZER
# =============================================================================
print("=" * 60)
print("[STEP 3] Load model Qwen2.5-7B-Instruct (4-bit QLoRA)")
print("=" * 60)

from unsloth import FastLanguageModel

MAX_SEQ_LENGTH = 256   # sesuai hasil P95 EDA
DTYPE          = None  # auto-detect (bf16 / fp16)
LOAD_IN_4BIT   = True  # hemat VRAM

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name    = "Qwen/Qwen2.5-7B-Instruct",
    max_seq_length = MAX_SEQ_LENGTH,
    dtype          = DTYPE,
    load_in_4bit   = LOAD_IN_4BIT,
)
print("  ✓ Model berhasil di-load\n")


# =============================================================================
# STEP 4 – SETUP LORA ADAPTERS (PEFT)
# =============================================================================
print("=" * 60)
print("[STEP 4] Konfigurasi LoRA adapters")
print("=" * 60)

model = FastLanguageModel.get_peft_model(
    model,
    r               = 16,
    target_modules  = ["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
    lora_alpha      = 16,
    lora_dropout    = 0,
    bias            = "none",
    use_gradient_checkpointing = "unsloth",  # sangat hemat VRAM
    random_state    = 3407,
)
print("  ✓ LoRA adapters siap\n")


# =============================================================================
# STEP 5 – LOAD & FORMAT DATASET
# =============================================================================
print("=" * 60)
print("[STEP 5] Load & format dataset")
print("=" * 60)

from datasets import load_dataset

dataset = load_dataset(
    "json",
    data_files = str(CLEANED_FILE),
    split      = "train",
)
print(f"  ✓ Jumlah sampel  : {len(dataset):,}")

def formatting_prompts_func(examples):
    """Terapkan chat template Qwen ke setiap baris messages."""
    texts = [
        tokenizer.apply_chat_template(
            msgs,
            tokenize              = False,
            add_generation_prompt = False,
        )
        for msgs in examples["messages"]
    ]
    return {"text": texts}

dataset = dataset.map(formatting_prompts_func, batched=True)
print(f"  ✓ Dataset selesai diformat\n")

# Preview 1 sampel
print("  [Preview sampel pertama]")
print("  " + dataset[0]["text"][:300].replace("\n", "\n  ") + "...\n")


# =============================================================================
# STEP 6 – KONFIGURASI & JALANKAN TRAINING
# =============================================================================
print("=" * 60)
print("[STEP 6] Mulai training SFT")
print("=" * 60)

from trl import SFTTrainer
from transformers import TrainingArguments, EarlyStoppingCallback

# ── Hyperparameter training ───────────────────────────────────────────────────
NUM_EPOCHS          = 3      # jumlah epoch maksimal
EARLY_STOP_PATIENCE = 3      # berhenti jika eval_loss tidak turun selama N eval
EVAL_STEPS          = 200    # evaluasi setiap N steps
# ─────────────────────────────────────────────────────────────────────────────

# Split 90% train / 10% eval untuk early stopping & load_best_model
dataset_split = dataset.train_test_split(test_size=0.1, seed=3407)
train_dataset = dataset_split["train"]
eval_dataset  = dataset_split["test"]
print(f"  ✓ Train: {len(train_dataset):,} sampel | Eval: {len(eval_dataset):,} sampel")

trainer = SFTTrainer(
    model              = model,
    tokenizer          = tokenizer,
    train_dataset      = train_dataset,
    eval_dataset       = eval_dataset,
    dataset_text_field = "text",
    max_seq_length     = MAX_SEQ_LENGTH,
    dataset_num_proc   = 2,
    callbacks          = [EarlyStoppingCallback(early_stopping_patience=EARLY_STOP_PATIENCE)],
    args = TrainingArguments(
        per_device_train_batch_size  = 4,
        gradient_accumulation_steps  = 4,
        warmup_steps                 = 5,
        num_train_epochs             = NUM_EPOCHS,   # epoch penuh, bukan max_steps
        learning_rate                = 2e-4,
        fp16                         = not torch.cuda.is_bf16_supported(),
        bf16                         = torch.cuda.is_bf16_supported(),
        logging_steps                = 10,
        evaluation_strategy          = "steps",      # evaluasi per N steps
        eval_steps                   = EVAL_STEPS,
        save_strategy                = "steps",      # simpan checkpoint per N steps
        save_steps                   = EVAL_STEPS,
        save_total_limit             = 3,            # simpan 3 checkpoint terbaik
        load_best_model_at_end       = True,         # otomatis load epoch terbaik
        metric_for_best_model        = "eval_loss",
        greater_is_better            = False,
        optim                        = "adamw_8bit",
        weight_decay                 = 0.01,
        lr_scheduler_type            = "linear",
        seed                         = 3407,
        output_dir                   = str(TRAIN_OUTPUT),
        report_to                    = "none",       # matikan wandb dll
    ),
)

trainer_stats = trainer.train()
print(f"\n  ✓ Training selesai")
print(f"  Best epoch/step : {trainer.state.best_model_checkpoint}")
print(f"  Best eval loss  : {trainer.state.best_metric:.4f}")
print(f"  Runtime         : {trainer_stats.metrics.get('train_runtime', 0):.1f}s")
print(f"  Train loss      : {trainer_stats.metrics.get('train_loss', 0):.4f}\n")


# =============================================================================
# STEP 7 – SIMPAN MODEL (LoRA adapters)
# =============================================================================
print("=" * 60)
print("[STEP 7] Simpan model")
print("=" * 60)

model.save_pretrained(str(OUTPUT_MODEL))
tokenizer.save_pretrained(str(OUTPUT_MODEL))
print(f"  ✓ Model disimpan di: {OUTPUT_MODEL}\n")


# =============================================================================
# STEP 8 – INFERENSI / TES MANUAL
# =============================================================================
print("=" * 60)
print("[STEP 8] Tes inferensi manual")
print("=" * 60)

FastLanguageModel.for_inference(model)  # aktifkan mode inferensi (lebih cepat)

def test_profil(usia, pendidikan, pendapatan, anggota, listrik, rasio):
    """
    Uji model dengan 1 profil rumah tangga.

    Parameter
    ---------
    usia       : int   – usia kepala keluarga (tahun)
    pendidikan : str   – tingkat pendidikan (sd / smp / sma / d3 / s1 / …)
    pendapatan : int   – pendapatan bulanan (Rupiah)
    anggota    : int   – jumlah anggota keluarga
    listrik    : int   – daya listrik terpasang (VA)
    rasio      : float – luas bangunan per kapita (m²/orang)
    """
    prompt = (
        f"Analisis profil: Kepala keluarga {usia} thn ({pendidikan}). "
        f"Pendapatan Rp{pendapatan:,} dengan {anggota} anggota. "
        f"Fisik: Listrik {listrik} VA, Rasio Luas {rasio:.1f} m2/kapita."
    )

    messages = [
        {"role": "system",  "content": "Anda adalah asisten ahli klasifikasi kesejahteraan sosial."},
        {"role": "user",    "content": prompt},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize              = True,
        add_generation_prompt = True,
        return_tensors        = "pt",
        padding               = True,
    ).to("cuda")

    outputs = model.generate(
        input_ids      = inputs,
        attention_mask = (inputs != tokenizer.pad_token_id).long(),
        max_new_tokens = 150,
        use_cache      = True,
        temperature    = 0.1,
    )

    full_text = tokenizer.batch_decode(outputs)[0]
    # Ambil hanya bagian jawaban asisten
    answer = full_text.split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
    return answer

# Contoh inferensi
print(test_profil(42, "sd", 800_000, 6, 450, 6.2))


# =============================================================================
# STEP 9 – EVALUASI BATCH (100 sampel dari dataset)
# =============================================================================
print("\n" + "=" * 60)
print("[STEP 9] Evaluasi batch (100 sampel)")
print("=" * 60)

from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib
matplotlib.use("Agg")          # non-interactive backend (aman di server)
import matplotlib.pyplot as plt

NUM_TEST    = 100
test_results = []

with open(CLEANED_FILE, "r", encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip()][:NUM_TEST]

print(f"  Mengevaluasi {len(lines)} sampel …")

for line in tqdm(lines, desc="  Eval"):
    data        = json.loads(line)
    msgs        = data["messages"]
    ground_truth = msgs[2]["content"] if len(msgs) > 2 else ""

    # Ekstrak label ground truth
    true_label = (
        ground_truth.split("Kesimpulan: ")[-1]
                    .split("<|im_end|>")[0]
                    .replace(".", "")
                    .strip()
    )

    # Inferensi
    inputs = tokenizer.apply_chat_template(
        [msgs[0], msgs[1]],
        tokenize              = True,
        add_generation_prompt = True,
        return_tensors        = "pt",
    ).to("cuda")

    outputs    = model.generate(input_ids=inputs, max_new_tokens=100, temperature=0.1)
    pred_text  = tokenizer.batch_decode(outputs)[0].split("<|im_start|>assistant\n")[-1]

    try:
        pred_label = (
            pred_text.split("Kesimpulan: ")[-1]
                     .split("<|im_end|>")[0]
                     .replace(".", "")
                     .strip()
        )
    except Exception:
        pred_label = "ERROR_PARSING"

    test_results.append({
        "input":         msgs[1]["content"],
        "true":          true_label,
        "pred":          pred_label,
        "full_response": pred_text,
    })

# ── Hitung akurasi ────────────────────────────────────────────────────────────
df_eval  = pd.DataFrame(test_results)
accuracy = (df_eval["true"] == df_eval["pred"]).mean()
print(f"\n  ✓ Akurasi Model : {accuracy * 100:.2f}%")
print(classification_report(df_eval["true"], df_eval["pred"]))

# ── Confusion Matrix ──────────────────────────────────────────────────────────
labels = sorted(df_eval["true"].unique())
cm     = confusion_matrix(df_eval["true"], df_eval["pred"], labels=labels)

plt.figure(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt="d",
            xticklabels=labels, yticklabels=labels, cmap="Blues")
plt.xlabel("Prediksi Model")
plt.ylabel("Ground Truth")
plt.title("Confusion Matrix – Klasifikasi Kemiskinan (data_crawl_clean)")
plt.tight_layout()

cm_path = BASE_DIR / "outputs" / "confusion_matrix_crawl.png"
plt.savefig(cm_path, dpi=150)
print(f"  ✓ Confusion matrix disimpan: {cm_path}")

# ── Tampilkan contoh kesalahan ────────────────────────────────────────────────
errors = df_eval[df_eval["true"] != df_eval["pred"]]
if not errors.empty:
    print(f"\n  --- {len(errors)} Contoh Kesalahan Model ---")
    print(errors[["true", "pred", "full_response"]].head(3).to_string(index=False))
else:
    print("\n  ✓ Tidak ada kesalahan klasifikasi pada 100 sampel pertama!")

print("\n[✓] Semua step selesai.")