#!/usr/bin/env python3
"""
SFT Training — Qwen2.5-0.5B-AITF (dari CPT Lokal)
====================================================
Supervised Fine-Tuning (SFT) menggunakan base model hasil CPT yang disimpan
di folder lokal.

Penggunaan:
    # 1. Install dependencies terlebih dahulu:
    #    pip install -r requirements.txt
    #
    # 2. Jalankan training:
    #    python train-sft.py

Argumen utama:
    --cpt-model-path   Path ke folder model CPT (default: ./model-Qwen2.5-0.5B-AITF-CPT)
    --jsonl-path       Path ke file dataset JSONL   (default: ./data/output.jsonl)
    --output-dir       Folder output checkpoint      (default: ./checkpoints)
    --merged-dir       Folder merged model           (default: ./merged_model)
    --epochs           Jumlah epoch                  (default: 3)
    --lr               Learning rate                 (default: 2e-4)
    --max-seq-len      Panjang sequence maksimum     (default: 512)
    --no-merge         Skip merge LoRA ke base model
    --no-eval          Skip evaluasi ROUGE setelah training
    --eval-subset      Jumlah sampel untuk evaluasi  (default: 500)
    --hf-repo-id       HuggingFace repo ID untuk push (opsional)
    --hf-token         HuggingFace API token         (opsional)
    --wandb-key        W&B API key                   (opsional)
    --wandb-project    W&B project name
    --wandb-entity     W&B entity/team
"""

import os
import sys
import subprocess
print("\n⚙️ [INIT] Menyuntikkan vaksin penghapus 'torchao' agar PEFT dan Transformers aman...")
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import json
import math
import random
import warnings
import gc
import re
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Argument Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="SFT Training Qwen2.5-0.5B-AITF dari model CPT lokal",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Path arguments
    parser.add_argument("--cpt-model-path", type=str,
                        default="/home/jovyan/Testing/output/qwen_cpt_v3_final",
                        help="Path ke folder model CPT lokal")
    parser.add_argument("--jsonl-path", type=str,
                        default="/home/jovyan/Testing/Data/data_sft.jsonl",
                        help="Path ke dataset JSONL SFT")
    parser.add_argument("--output-dir", type=str,
                        default="/home/jovyan/Testing/output/sft_qwen_05b_final",
                        help="Folder output untuk checkpoint SFT")
    parser.add_argument("--merged-dir", type=str,
                        default="/home/jovyan/Testing/output/sft_qwen_05b_final_merged",
                        help="Folder untuk merged model hasil SFT")

    # Training hyperparameters
    parser.add_argument("--epochs", type=int, default=3,
                        help="Jumlah epoch training")
    parser.add_argument("--lr", type=float, default=2e-4,
                        help="Learning rate")
    parser.add_argument("--max-seq-len", type=int, default=1024,
                        help="Panjang sequence maksimum")
    parser.add_argument("--train-ratio", type=float, default=0.90,
                        help="Rasio data training")
    parser.add_argument("--val-ratio", type=float, default=0.08,
                        help="Rasio data validasi")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")

    # LoRA config
    parser.add_argument("--lora-r", type=int, default=16,
                        help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32,
                        help="LoRA alpha")
    parser.add_argument("--lora-dropout", type=float, default=0.05,
                        help="LoRA dropout")

    # Behavior flags
    parser.add_argument("--no-merge", action="store_true",
                        help="Skip merge LoRA ke base model setelah training")
    parser.add_argument("--no-eval", action="store_true",
                        help="Skip evaluasi ROUGE setelah training")
    parser.add_argument("--eval-subset", type=int, default=500,
                        help="Jumlah sampel untuk evaluasi ROUGE")

    # W&B config
    parser.add_argument("--wandb-key", type=str,
                        default="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",
                        help="W&B API key")
    parser.add_argument("--wandb-project", type=str,
                        default="qwen2.5-0.5B-Instruct-aitf-cpt-sft",
                        help="W&B project name")
    parser.add_argument("--wandb-entity", type=str,
                        default="redityaimanuel-universitas-br",
                        help="W&B entity/team")

    # HuggingFace Hub (opsional)
    parser.add_argument("--hf-repo-id", type=str, default="",
                        help="HuggingFace repo ID (kosong = tidak push)")
    parser.add_argument("--hf-token", type=str, default="",
                        help="HuggingFace API token")

    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Imports berat (setelah argparse, agar --help cepat)
# ─────────────────────────────────────────────────────────────────────────────

import torch
import transformers
import wandb
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, TaskType, get_peft_model, PeftModel
from trl import SFTTrainer, SFTConfig
from datasets import Dataset

warnings.filterwarnings("ignore")
transformers.logging.set_verbosity_error()


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Anda adalah sistem ahli analisis profil kesejahteraan sosial yang objektif dan presisi. 

Tugas Anda:
1. Menganalisis kondisi sosial-ekonomi keluarga berdasarkan deskripsi yang diberikan.
2. Memberikan penalaran (reasoning) komprehensif yang mencakup aspek:
- Kepemilikan aset dan kualitas hunian.
- Komposisi anggota keluarga dan beban ketergantungan.
- Stabilitas pendapatan dan akses kebutuhan dasar.

3. Menentukan skor evaluasi internal (0-100) dan estimasi desil nasional (1-10) berdasarkan kriteria kemiskinan makro yang berlaku.

Gunakan format output berikut:
- Analisis Kondisi: (Bedah poin-poin krusial dari deskripsi)
- Reasoning: (Penjelasan mengapa keluarga tersebut masuk ke kategori skor/desil tertentu, hubungkan antar variabel)
- Skor Evaluasi: [Angka]
- Desil Nasional: [Angka 1-10]
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Load Dataset
# ─────────────────────────────────────────────────────────────────────────────

def load_jsonl(filepath: str) -> list:
    """Load JSONL dan validasi skema system/user/assistant."""
    records, errors = [], 0
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec  = json.loads(line)
                msgs = rec["messages"]
                assert [m["role"] for m in msgs] == ["system", "user", "assistant"]
                assert all(m["content"].strip() for m in msgs)
                records.append(rec)
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"⚠️  Baris {i}: {e}")
    print(f"\n📊 Records valid : {len(records):,}")
    print(f"   Errors/skip    : {errors:,}")
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Dataset Stats
# ─────────────────────────────────────────────────────────────────────────────

def stats(lst, label):
    s = sorted(lst); n = len(s)
    print(f"   {label:18s} mean={sum(s)/n:>5.0f}  "
          f"min={s[0]:>4d}  max={s[-1]:>4d}  "
          f"p95={s[int(n*.95)]:>4d}  p99={s[int(n*.99)]:>4d}")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Format Dataset ke HF Dataset
# ─────────────────────────────────────────────────────────────────────────────

def make_formatter(tokenizer):
    """Kembalikan fungsi format_chatml yang capture tokenizer via closure."""
    def format_chatml(example: dict) -> dict:
        msgs = example["messages"]
        # Override system prompt dengan versi terbaru
        msgs[0]["content"] = SYSTEM_PROMPT
        text = tokenizer.apply_chat_template(
            msgs,
            tokenize              = False,
            add_generation_prompt = False,
        )
        return {"text": text}
    return format_chatml


def to_hf_dataset(records: list, tokenizer) -> Dataset:
    raw = Dataset.from_dict({"messages": [r["messages"] for r in records]})
    return raw.map(make_formatter(tokenizer), remove_columns=["messages"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Inferensi
# ─────────────────────────────────────────────────────────────────────────────

def predict(inf_model, inf_tok, user_text: str, max_new_tokens: int = 150) -> str:
    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_text},
    ]
    prompt = inf_tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = inf_tok(prompt, return_tensors="pt").to(inf_model.device)

    with torch.no_grad():
        output_ids = inf_model.generate(
            **inputs,
            max_new_tokens     = max_new_tokens,
            do_sample          = False,
            repetition_penalty = 1.1,
            pad_token_id       = inf_tok.pad_token_id,
            eos_token_id       = inf_tok.eos_token_id,
        )
    new_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
    return inf_tok.decode(new_ids, skip_special_tokens=True).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # Format path absolut langsung sesuai argumen terminal Linux
    CPT_MODEL_PATH  = Path(args.cpt_model_path).expanduser().resolve()
    JSONL_PATH      = Path(args.jsonl_path).expanduser().resolve()
    OUTPUT_DIR      = Path(args.output_dir).expanduser().resolve()
    MERGED_DIR      = Path(args.merged_dir).expanduser().resolve()

    # ── 1. Info Environment ────────────────────────────────────────────────
    print("=" * 70)
    print("🚀 SFT Training — Qwen2.5-0.5B-AITF (dari CPT Lokal)")
    print("=" * 70)
    print(f"✅ PyTorch        : {torch.__version__}")
    print(f"✅ Transformers   : {transformers.__version__}")
    print(f"✅ W&B            : {wandb.__version__}")
    print(f"✅ CUDA available : {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"✅ GPU            : {torch.cuda.get_device_name(0)}")
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"✅ VRAM           : {vram:.1f} GB")

    # ── 2. Konfigurasi Path ────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Konfigurasi Path:")
    print(f"   CPT Model  : {CPT_MODEL_PATH}")
    print(f"   JSONL      : {JSONL_PATH}")
    print(f"   Output     : {OUTPUT_DIR}")
    print(f"   Merged     : {MERGED_DIR}")

    # Validasi keberadaan file/folder
    assert CPT_MODEL_PATH.is_dir(), f"❌ Folder CPT tidak ditemukan: {CPT_MODEL_PATH}"
    assert (CPT_MODEL_PATH / "model.safetensors").is_file(), \
        "❌ model.safetensors tidak ada di folder CPT!"
    assert JSONL_PATH.is_file(), f"❌ File JSONL tidak ditemukan: {JSONL_PATH}"

    cpt_size  = (CPT_MODEL_PATH / "model.safetensors").stat().st_size / 1e6
    jsonl_size = JSONL_PATH.stat().st_size / 1e6
    print(f"\n✅ CPT model ditemukan!  (model.safetensors: {cpt_size:.0f} MB)")
    print(f"✅ Dataset JSONL ditemukan!  ({jsonl_size:.1f} MB)")

    # ── 3. GPU Check & Compute Config ─────────────────────────────────────
    # Jalankan nvidia-smi untuk info GPU
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        print("\n" + result.stdout)
    except FileNotFoundError:
        print("⚠️  nvidia-smi tidak tersedia")

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb  = torch.cuda.get_device_properties(0).total_memory / 1e9
        USE_BF16 = torch.cuda.is_bf16_supported()
        DTYPE    = torch.bfloat16 if USE_BF16 else torch.float16

        print(f"\n🖥️  GPU    : {gpu_name}")
        print(f"💾 VRAM   : {vram_gb:.1f} GB")
        print(f"🔢 Dtype  : {'bfloat16' if USE_BF16 else 'float16'}")

        if vram_gb >= 40:
            PER_DEVICE_BATCH = 8; GRAD_ACCUM = 2
        elif vram_gb >= 20:
            PER_DEVICE_BATCH = 4; GRAD_ACCUM = 4
        else:  # T4 ~16 GB atau lebih kecil
            PER_DEVICE_BATCH = 2; GRAD_ACCUM = 8

        EFFECTIVE_BATCH = PER_DEVICE_BATCH * GRAD_ACCUM
        print(f"📦 Batch/device : {PER_DEVICE_BATCH}  (grad_accum={GRAD_ACCUM})")
        print(f"📦 Effective    : {EFFECTIVE_BATCH}")
    else:
        print("❌ GPU tidak tersedia — pastikan server memiliki GPU!")
        DTYPE, PER_DEVICE_BATCH, GRAD_ACCUM, USE_BF16 = torch.float32, 1, 1, False

    # ── 4. W&B Setup ──────────────────────────────────────────────────────
    WANDB_PROJECT  = args.wandb_project
    WANDB_ENTITY   = args.wandb_entity
    WANDB_RUN_NAME = f"qwen2.5-0.5b-cpt-sft-{datetime.now():%Y%m%d-%H%M}"

    if args.wandb_key:
        wandb.login(key=args.wandb_key)
        print("✅ W&B login berhasil!")
    else:
        wandb.login()
        print("✅ W&B login (interaktif)")

    os.environ["WANDB_PROJECT"]   = WANDB_PROJECT
    os.environ["WANDB_LOG_MODEL"] = "checkpoint"
    if WANDB_ENTITY:
        os.environ["WANDB_ENTITY"] = WANDB_ENTITY

    print(f"\n📊 W&B Config:")
    print(f"   Project  : {WANDB_PROJECT}")
    print(f"   Run Name : {WANDB_RUN_NAME}")

    # ── 5. Load & Validasi Dataset ─────────────────────────────────────────
    raw_data = load_jsonl(str(JSONL_PATH))

    print("\n🔍 Contoh record pertama:")
    for msg in raw_data[0]["messages"]:
        preview = msg["content"][:120].replace("\n", " ")
        print(f"  [{msg['role'].upper():9s}] {preview}...")

    # Split dataset
    TRAIN_RATIO = args.train_ratio
    VAL_RATIO   = args.val_ratio

    random.seed(args.seed)
    random.shuffle(raw_data)

    total   = len(raw_data)
    n_train = int(total * TRAIN_RATIO)
    n_val   = int(total * VAL_RATIO)

    train_data = raw_data[:n_train]
    val_data   = raw_data[n_train : n_train + n_val]
    test_data  = raw_data[n_train + n_val:]

    print(f"\n📂 Dataset Split:")
    print(f"   Train  : {len(train_data):,}  ({TRAIN_RATIO*100:.0f}%)")
    print(f"   Val    : {len(val_data):,}   ({VAL_RATIO*100:.0f}%)")
    print(f"   Test   : {len(test_data):,}   (sisa)")
    print(f"   Total  : {total:,}")

    # ── 6. EDA ────────────────────────────────────────────────────────────
    sample_n = min(3_000, total)
    sample   = random.sample(raw_data, sample_n)

    total_toks, user_toks, asst_toks = [], [], []
    for rec in sample:
        msgs = rec["messages"]
        total_toks.append(sum(len(m["content"]) // 4 for m in msgs))
        user_toks.append(len(msgs[1]["content"]) // 4)
        asst_toks.append(len(msgs[2]["content"]) // 4)

    print(f"\n📊 Token Stats (heuristik, n={sample_n:,}):")
    stats(total_toks, "Total/record")
    stats(user_toks,  "User content")
    stats(asst_toks,  "Assistant")

    # Init W&B
    wandb.init(
        project = WANDB_PROJECT,
        entity  = WANDB_ENTITY or None,
        name    = WANDB_RUN_NAME,
        config  = {
            "base_model"     : "CPT-Qwen2.5-0.5B-AITF (lokal)",
            "cpt_model_path" : str(CPT_MODEL_PATH),
            "method"         : "SFT + QLoRA 4-bit",
            "lora_r"         : args.lora_r,
            "lora_alpha"     : args.lora_alpha,
            "dataset"        : "DTSEN-Malang ChatML",
            "total_records"  : total,
            "train_records"  : len(train_data),
            "val_records"    : len(val_data),
            "avg_tokens"     : round(sum(total_toks) / len(total_toks)),
            "max_tokens"     : max(total_toks),
        },
        tags   = ["sft", "qlora", "qwen2.5", "dtsen", "cpt-base", "bahasa-indonesia"],
        reinit = True,
    )

    # Distribusi desil
    print("\n🎯 Distribusi Desil Nasional:")
    counter = {}
    for rec in sample:
        m = re.search(r"Desil Nasional[\:\s]*(\d+)", rec["messages"][2]["content"])
        if m:
            d = int(m.group(1))
            counter[d] = counter.get(d, 0) + 1

    wandb.log({"desil_distribution": wandb.plot.bar(
        wandb.Table(columns=["Desil", "Count"],
                    data=[[f"Desil {d}", counter[d]] for d in sorted(counter)]),
        "Desil", "Count", title="Distribusi Desil Nasional di Dataset",
    )})

    for d in sorted(counter):
        bar = "█" * min(counter[d] // 5, 50)
        print(f"  Desil {d:2d}: {counter[d]:4d} {bar}")

    print("\n✅ EDA ter-log ke W&B")

    # ── 7. Load Tokenizer ──────────────────────────────────────────────────
    print(f"\n📥 Loading tokenizer dari CPT lokal: {CPT_MODEL_PATH} ...")
    tokenizer = AutoTokenizer.from_pretrained(
        str(CPT_MODEL_PATH),
        trust_remote_code = True,
        padding_side      = "right",
        local_files_only  = True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 🔧 [FIX] Pasang chat_template bawaan Qwen jika hilang saat CPT
    if getattr(tokenizer, "chat_template", None) is None:
        print("⚠️  chat_template kosong! Memasang template ChatML standar Qwen...")
        tokenizer.chat_template = (
            "{% for message in messages %}"
            "{{'<|im_start|>' + message['role'] + '\\n' + message['content'] + '<|im_end|>\\n'}}"
            "{% endfor %}"
            "{% if add_generation_prompt %}"
            "{{ '<|im_start|>assistant\\n' }}"
            "{% endif %}"
        )

    print(f"✅ Vocab size   : {tokenizer.vocab_size:,}")
    print(f"✅ pad_token    : {tokenizer.pad_token!r}")
    print(f"✅ eos_token    : {tokenizer.eos_token!r}")

    # ── 8. Load Model CPT (QLoRA 4-bit) ───────────────────────────────────
    bnb_config = BitsAndBytesConfig(
        load_in_4bit              = True,
        bnb_4bit_quant_type       = "nf4",
        bnb_4bit_compute_dtype    = DTYPE,
        bnb_4bit_use_double_quant = True,
    )

    print(f"\n📥 Loading model CPT (4-bit quantized) dari lokal...")
    print(f"   Path: {CPT_MODEL_PATH}")
    model = AutoModelForCausalLM.from_pretrained(
        str(CPT_MODEL_PATH),
        quantization_config = bnb_config,
        device_map          = "auto",
        trust_remote_code   = True,
        torch_dtype         = DTYPE,
        attn_implementation = "eager",
        local_files_only    = True,
    )
    model.config.use_cache      = False
    model.config.pretraining_tp = 1

    total_params     = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n✅ Model CPT berhasil di-load!")
    print(f"   Total params     : {total_params/1e6:.1f}M")
    print(f"   Trainable params : {trainable_params/1e6:.1f}M ({trainable_params/total_params*100:.1f}%)")

    # ── 9. LoRA Config ─────────────────────────────────────────────────────
    lora_config = LoraConfig(
        task_type      = TaskType.CAUSAL_LM,
        r              = args.lora_r,
        lora_alpha     = args.lora_alpha,
        lora_dropout   = args.lora_dropout,
        bias           = "none",
        target_modules = [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        inference_mode = False,
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    wandb.config.update({"trainable_params": trainable}, allow_val_change=True)

    # ── 10. Format Dataset ─────────────────────────────────────────────────
    print("\n⚙️  Memformat dataset...")
    train_ds = to_hf_dataset(train_data, tokenizer)
    val_ds   = to_hf_dataset(val_data, tokenizer)
    test_ds  = to_hf_dataset(test_data, tokenizer)

    print(f"✅ Train  : {len(train_ds):,} samples")
    print(f"✅ Val    : {len(val_ds):,} samples")
    print(f"✅ Test   : {len(test_ds):,} samples")

    print("\n🔍 Preview teks terformat (300 karakter pertama):")
    print(train_ds[0]["text"][:300])

    # ── 11. SFT Config ─────────────────────────────────────────────────────
    MAX_SEQ_LEN = args.max_seq_len
    NUM_EPOCHS  = args.epochs
    LR          = args.lr

    sft_config = SFTConfig(
        # ── Output ──────────────────────────────────────────────────────────
        output_dir                  = str(OUTPUT_DIR),
        run_name                    = WANDB_RUN_NAME,

        # ── Epoch & Batch ────────────────────────────────────────────────────
        num_train_epochs            = NUM_EPOCHS,
        per_device_train_batch_size = PER_DEVICE_BATCH,
        per_device_eval_batch_size  = PER_DEVICE_BATCH,
        gradient_accumulation_steps = GRAD_ACCUM,

        # ── Optimisasi ───────────────────────────────────────────────────────
        learning_rate               = LR,
        lr_scheduler_type           = "cosine",
        warmup_ratio                = 0.05,
        weight_decay                = 0.01,
        optim                       = "paged_adamw_8bit",
        max_grad_norm               = 1.0,
        fp16                        = not USE_BF16,
        bf16                        = USE_BF16,

        # ── Evaluasi & Logging ───────────────────────────────────────────────
        eval_strategy               = "steps",
        eval_steps                  = 500,
        logging_steps               = 50,
        save_strategy               = "steps",
        save_steps                  = 500,
        save_total_limit            = 3,
        load_best_model_at_end      = True,
        metric_for_best_model       = "eval_loss",
        greater_is_better           = False,

        # ── W&B Integration ──────────────────────────────────────────────────
        report_to                   = "wandb",
        logging_first_step          = True,

        # ── Misc ─────────────────────────────────────────────────────────────
        dataloader_num_workers      = 2,
        seed                        = args.seed,
    )

    wandb.config.update({
        "num_epochs"     : NUM_EPOCHS,
        "learning_rate"  : LR,
        "max_seq_length" : MAX_SEQ_LEN,
        "effective_batch": PER_DEVICE_BATCH * GRAD_ACCUM,
        "optimizer"      : "paged_adamw_8bit",
        "lr_scheduler"   : "cosine",
        "packing"        : True,
    }, allow_val_change=True)

    print("✅ SFTConfig siap!")
    print(f"   Epochs          : {NUM_EPOCHS}")
    print(f"   Effective batch : {PER_DEVICE_BATCH * GRAD_ACCUM}")
    print(f"   Learning rate   : {LR}")
    print(f"   Max seq length  : {MAX_SEQ_LEN}")
    print(f"   Report to       : wandb ({WANDB_PROJECT})")

    # ── 12. SFT Training ───────────────────────────────────────────────────
    from transformers import TrainerCallback
    
    class MultiHubDriveUploadCallback(TrainerCallback):
        def on_save(self, trainer_args, state, control, **kwargs):
            checkpoint_dir = f"{trainer_args.output_dir}/checkpoint-{state.global_step}"
            print(f"\n📤 [Callback SFT] Mengunggah SFT checkpoint langkah {state.global_step} ke Google Drive...")
            try:
                # Patokan absolutan file upload uploader script milik AITF
                upload_script = "/home/jovyan/Testing/Training/Core/upload_model_drive.py"
                if not Path(upload_script).exists():
                    upload_script = "upload_model_drive.py"  # Fallback kalau dijalankan di folder yg sama
                subprocess.run([sys.executable, upload_script, checkpoint_dir], check=False)
                print("✅ Upload SFT Checkpoint ke Drive selesai")
            except Exception as e:
                print(f"⚠️ Gagal unggah SFT ke Drive: {e}")

    sft_callbacks = [MultiHubDriveUploadCallback()]

    trainer = SFTTrainer(
        model            = model,
        args             = sft_config,
        train_dataset    = train_ds,
        eval_dataset     = val_ds,
        processing_class = tokenizer,
        callbacks        = sft_callbacks,
    )

    print("\n🚀 Mulai SFT Training...")
    print(f"   Base model  : CPT-Qwen2.5-0.5B-AITF (lokal)")
    print(f"   Steps total ≈ {len(train_ds) * NUM_EPOCHS // (PER_DEVICE_BATCH * GRAD_ACCUM):,}")
    print(f"   W&B Run     : https://wandb.ai/{WANDB_ENTITY or '<username>'}/{WANDB_PROJECT}/runs/{wandb.run.id}")
    print()

    train_result = trainer.train()

    print("\n✅ Training selesai!")
    print(f"   Train loss  : {train_result.training_loss:.4f}")
    print(f"   Runtime     : {train_result.metrics.get('train_runtime', 0)/60:.1f} menit")
    print(f"   Samples/sec : {train_result.metrics.get('train_samples_per_second', 0):.1f}")

    # ── 13. Simpan LoRA Adapter ────────────────────────────────────────────
    ADAPTER_DIR = str(OUTPUT_DIR / "final_adapter")
    trainer.model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)
    print(f"✅ LoRA adapter tersimpan: {ADAPTER_DIR}")

    wandb.log({
        "final/train_loss"      : train_result.training_loss,
        "final/runtime_min"     : train_result.metrics.get("train_runtime", 0) / 60,
        "final/samples_per_sec" : train_result.metrics.get("train_samples_per_second", 0),
    })

    # ── 14. Merge LoRA ke Base Model ───────────────────────────────────────
    MERGE = not args.no_merge

    if MERGE:
        print("\n🔀 Merge LoRA adapter ke base model CPT...")
        gc.collect(); torch.cuda.empty_cache()

        base_model = AutoModelForCausalLM.from_pretrained(
            str(CPT_MODEL_PATH),
            torch_dtype       = DTYPE,
            device_map        = "auto",
            trust_remote_code = True,
            local_files_only  = True,
        )
        merged = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
        merged = merged.merge_and_unload()

        merged.save_pretrained(str(MERGED_DIR), safe_serialization=True)
        tokenizer.save_pretrained(str(MERGED_DIR))
        print(f"✅ Merged model tersimpan: {MERGED_DIR}")
    else:
        print("⏭️  Merge dilewati (--no-merge)")

    # ── 15. Push ke HuggingFace Hub (opsional) ────────────────────────────
    HF_REPO_ID = args.hf_repo_id
    HF_TOKEN   = args.hf_token

    if HF_REPO_ID and HF_TOKEN:
        from huggingface_hub import login
        login(token=HF_TOKEN)
        model_to_push = merged if MERGE else trainer.model
        model_to_push.push_to_hub(HF_REPO_ID)
        tokenizer.push_to_hub(HF_REPO_ID)
        print(f"✅ Model dipush ke: https://huggingface.co/{HF_REPO_ID}")
        wandb.log({"hf_model_url": f"https://huggingface.co/{HF_REPO_ID}"})
    else:
        print("⏭️  Push ke Hub dilewati")

    # Tutup W&B training run
    wandb.finish()
    print(f"\n✅ W&B run selesai! Lihat hasil di:")
    print(f"   https://wandb.ai/{WANDB_ENTITY or '<username>'}/{WANDB_PROJECT}")

    # ── 16. Inferensi Uji ──────────────────────────────────────────────────
    gc.collect(); torch.cuda.empty_cache()

    if MERGE:
        inf_model = AutoModelForCausalLM.from_pretrained(
            str(MERGED_DIR), torch_dtype=DTYPE, device_map="auto", trust_remote_code=True,
        )
        inf_tok = AutoTokenizer.from_pretrained(str(MERGED_DIR), trust_remote_code=True)
    else:
        base_m = AutoModelForCausalLM.from_pretrained(
            str(CPT_MODEL_PATH), quantization_config=bnb_config,
            device_map="auto", trust_remote_code=True, local_files_only=True,
        )
        inf_model = PeftModel.from_pretrained(base_m, ADAPTER_DIR)
        inf_tok   = tokenizer

    inf_model.eval()
    print("✅ Model siap untuk inferensi!")

    print("=" * 70)
    for i, rec in enumerate(test_data[:5], 1):
        user_text  = rec["messages"][1]["content"]
        expected   = rec["messages"][2]["content"]
        prediction = predict(inf_model, inf_tok, user_text)

        print(f"\n[Sampel {i}]")
        print(f"  Expected   : {expected[:200]}")
        print(f"  Prediction : {prediction[:200]}")
    print("=" * 70)

    # Uji manual
    user_input = """Profil Keluarga:

[Demografi & Lokasi]
Keluarga ini berlokasi di Kelurahan Mergosono, Kecamatan Kedungkandang,
Kota Malang, Provinsi Jawa Timur. Keluarga terdiri dari 4 orang anggota.
Keluarga ini tidak tercatat sebagai penerima bantuan iuran (non-PBI).

[Kondisi Perumahan]
Mereka menempati rumah berstatus milik sendiri dengan luas lantai 72 meter persegi.
Jenis lantai: keramik; dinding: tembok; atap: genteng.
Sumber air minum utama dari air isi ulang. Penerangan utama menggunakan
listrik PLN dengan meteran dengan daya terpasang 1.300 watt.
Bahan bakar utama untuk memasak adalah gas elpiji 3 kg.

[Kepemilikan Aset]
Aset bergerak yang dimiliki: televisi datar, smartphone, kulkas.
Tidak memiliki lahan atau rumah lain. Tidak memiliki hewan ternak."""

    result = predict(inf_model, inf_tok, user_input)
    print(f"\n🤖 Prediksi Model SFT:")
    print(result)

    # ── 17. Evaluasi ROUGE ─────────────────────────────────────────────────
    if args.no_eval:
        print("\n⏭️  Evaluasi ROUGE dilewati (--no-eval)")
        return

    try:
        from rouge_score import rouge_scorer as rs_lib
    except ImportError:
        print("\n⚠️  rouge-score tidak terinstall, skip evaluasi ROUGE")
        print("   Install dengan: pip install rouge-score")
        return

    EVAL_SUBSET = min(args.eval_subset, len(test_data))
    eval_sample = test_data[:EVAL_SUBSET]

    scorer = rs_lib.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=False)
    exact = 0
    r1_list, r2_list, rl_list = [], [], []
    gt_counter, pred_counter, error_counter = {}, {}, {}

    print(f"\n📊 Evaluasi pada {EVAL_SUBSET:,} sampel test set...")
    for i, rec in enumerate(eval_sample):
        user_text = rec["messages"][1]["content"]
        ref       = rec["messages"][2]["content"].strip()
        pred      = predict(inf_model, inf_tok, user_text).strip()

        if ref.lower() == pred.lower():
            exact += 1

        scores = scorer.score(ref, pred)
        r1_list.append(scores["rouge1"].fmeasure)
        r2_list.append(scores["rouge2"].fmeasure)
        rl_list.append(scores["rougeL"].fmeasure)

        m_gt   = re.search(r"Desil Nasional[\:\s]*(\d+)", ref)
        m_pred = re.search(r"Desil Nasional[\:\s]*(\d+)", pred)
        if m_gt:
            d = int(m_gt.group(1)); gt_counter[d] = gt_counter.get(d, 0) + 1
        if m_pred:
            d = int(m_pred.group(1)); pred_counter[d] = pred_counter.get(d, 0) + 1
        if m_gt and m_pred:
            err = abs(int(m_gt.group(1)) - int(m_pred.group(1)))
            error_counter[err] = error_counter.get(err, 0) + 1

        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{EVAL_SUBSET}")

    em_pct = exact / EVAL_SUBSET * 100
    r1_avg = sum(r1_list) / len(r1_list) * 100
    r2_avg = sum(r2_list) / len(r2_list) * 100
    rl_avg = sum(rl_list) / len(rl_list) * 100

    print(f"\n📊 Hasil Evaluasi (n={EVAL_SUBSET:,}):")
    print(f"   Exact Match : {em_pct:>6.2f}%")
    print(f"   ROUGE-1     : {r1_avg:>6.2f}%")
    print(f"   ROUGE-2     : {r2_avg:>6.2f}%")
    print(f"   ROUGE-L     : {rl_avg:>6.2f}%")

    exact_desil_pct = 0
    within1_pct     = 0
    total_parsed    = sum(error_counter.values())
    if total_parsed > 0:
        print("\n📊 Distribusi Error Desil (|prediksi - truth|):")
        for err in sorted(error_counter):
            pct = error_counter[err] / total_parsed * 100
            bar = "█" * min(int(pct), 40)
            print(f"  Selisih {err:>2}: {error_counter[err]:>4} ({pct:>5.1f}%) {bar}")
        exact_desil_pct = error_counter.get(0, 0) / total_parsed * 100
        within1_pct     = (error_counter.get(0,0) + error_counter.get(1,0)) / total_parsed * 100
        print(f"\n   Exact desil     : {exact_desil_pct:.1f}%")
        print(f"   Within ±1 desil : {within1_pct:.1f}%")

    # Log evaluasi ke W&B (run baru)
    wandb.init(
        project=WANDB_PROJECT, entity=WANDB_ENTITY or None,
        name=WANDB_RUN_NAME + "-eval", reinit=True,
    )
    wandb.log({
        "eval/exact_match_pct"  : em_pct,
        "eval/rouge1"           : r1_avg,
        "eval/rouge2"           : r2_avg,
        "eval/rougeL"           : rl_avg,
        "eval/n_samples"        : EVAL_SUBSET,
        "eval/exact_desil_pct"  : exact_desil_pct,
        "eval/within1_desil_pct": within1_pct,
    })
    wandb.finish()
    print("\n✅ Hasil evaluasi ter-log ke W&B!")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
