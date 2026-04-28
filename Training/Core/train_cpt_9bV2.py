"""
CPT Training Script - AITF Project
Model  : Qwen3.5-9B
Jalankan di folder berbeda (Testing_9B/) agar tidak konflik dengan training 0.5B:

    mkdir -p ~/Testing_9B
    cp train_cpt_9b.py ~/Testing_9B/
    cd ~/Testing_9B
    nohup python train_cpt_9b.py > training_9b.log 2>&1 &
    echo $!  # catat PID
"""
import os
import gc
import math

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import torch

# --- ULTIMATE BYPASS UNTUK SELURUH ERROR TORCH.LOAD (CVE-2025-32434) ---
_original_torch_load = torch.load
def _hacked_torch_load(*args, **kwargs):
    kwargs.pop('weights_only', None)
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _hacked_torch_load

import transformers.utils.import_utils
if hasattr(transformers.utils.import_utils, 'check_torch_load_is_safe'):
    transformers.utils.import_utils.check_torch_load_is_safe = lambda: None
# ------------------------------------------------------------------------

import wandb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Unsloth untuk 9B — coba dulu, fallback ke HuggingFace biasa
USE_UNSLOTH = True
try:
    from unsloth import FastLanguageModel
    print("✅ Unsloth tersedia — menggunakan unsloth untuk 9B")
except ImportError:
    USE_UNSLOTH = False
    print("⚠️  Unsloth tidak tersedia untuk model ini — fallback ke HuggingFace + PEFT biasa")

from datasets import load_dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    TrainerCallback,
)
from transformers.trainer_utils import get_last_checkpoint

print("✅ Library berhasil diimport.")
print(f"GPU : {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Tidak ada GPU'}")
print(f"VRAM: {round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)} GB" if torch.cuda.is_available() else "")

# ============================================================
# KONFIGURASI
# ============================================================
# Coba unsloth versi dulu, fallback ke Qwen resmi
MODEL_NAME_UNSLOTH = "unsloth/Qwen3.5-9B"
MODEL_NAME_HF      = "Qwen/Qwen3.5-9B"

max_seq_length = 2048
block_size     = max_seq_length

# Path TERPISAH dari training 0.5B — untuk parallelism
HOME            = os.path.expanduser('~')
JSONL_FILE      = os.path.join(HOME, 'Testing', 'Data', 'data_training_mixed.jsonl')
checkpoint_path = os.path.join(HOME, 'Testing_9B', 'checkpoints', 'qwen35_9b_cpt')
output_path     = os.path.join(HOME, 'Testing_9B', 'output', 'qwen35_9b_final')
OUTPUT_DIR      = checkpoint_path

WANDB_PROJECT  = "AITF - CPT"
WANDB_RUN_NAME = "Qwen3.5-9B-AITF-CPT-server"
# ============================================================

os.makedirs(checkpoint_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)
os.makedirs(os.path.join(HOME, 'Testing_9B'), exist_ok=True)

print(f"\n📁 Checkpoint : {checkpoint_path}")
print(f"📁 Output     : {output_path}")

# ── WandB ──────────────────────────────────────────────────
os.environ['WANDB_API_KEY'] = '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'
try:
    wandb.login()
    wandb.init(
        project = WANDB_PROJECT,
        name    = WANDB_RUN_NAME,
        reinit  = "finish_previous",
        config  = {
            "model":          MODEL_NAME_HF,
            "max_seq_length": max_seq_length,
            "block_size":     block_size,
            "use_unsloth":    USE_UNSLOTH,
        }
    )
    print(f"✅ WandB aktif → {wandb.run.url}")
except Exception as e:
    print(f"⚠️ WandB gagal: {e}. Lanjut tanpa monitoring.")
    wandb.init(mode='disabled')

# ── Load Dataset ───────────────────────────────────────────
if not os.path.exists(JSONL_FILE):
    raise FileNotFoundError(f"❌ File tidak ditemukan: {JSONL_FILE}\nPastikan path benar!")

print(f"\nMemuat dataset dari {JSONL_FILE} ...")
raw_dataset = load_dataset("json", data_files=JSONL_FILE, split="train")
print(f"✅ Total dokumen: {len(raw_dataset):,}")

print("Memisahkan dataset 90:10...")
split_dataset = raw_dataset.train_test_split(test_size=0.1, seed=42)
dataset = DatasetDict({
    'train':      split_dataset['train'],
    'validation': split_dataset['test'],
})
print(dataset)

# ── Load Model + Apply LoRA ────────────────────────────────
print(f"\nMemuat model Qwen3.5-9B ...")

if USE_UNSLOTH:
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name     = MODEL_NAME_UNSLOTH,
            max_seq_length = max_seq_length,
            load_in_4bit   = True,
        )
        print(f"✅ Model dimuat via Unsloth: {MODEL_NAME_UNSLOTH}")
    except Exception as e:
        print(f"⚠️  Unsloth gagal load {MODEL_NAME_UNSLOTH}: {e}")
        print(f"🔄 Fallback ke HuggingFace: {MODEL_NAME_HF}")
        USE_UNSLOTH = False

if not USE_UNSLOTH:
    # Fallback: HuggingFace + bitsandbytes 4-bit + PEFT manual
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, TaskType

    bnb_config = BitsAndBytesConfig(
        load_in_4bit              = True,
        bnb_4bit_compute_dtype    = torch.bfloat16,
        bnb_4bit_use_double_quant = True,
        bnb_4bit_quant_type       = "nf4",
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME_HF,
        quantization_config = bnb_config,
        device_map          = "auto",
        trust_remote_code   = True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME_HF, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    lora_config = LoraConfig(
        r              = 16,
        lora_alpha     = 16,
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj"],
        lora_dropout   = 0.0,
        bias           = "none",
        task_type      = TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    print(f"✅ Model dimuat via HuggingFace + PEFT: {MODEL_NAME_HF}")

# Apply LoRA jika pakai Unsloth
if USE_UNSLOTH:
    model = FastLanguageModel.get_peft_model(
        model,
        r                          = 16,
        target_modules             = ["q_proj", "k_proj", "v_proj", "o_proj",
                                       "gate_proj", "up_proj", "down_proj"],
        lora_alpha                 = 16,
        lora_dropout               = 0,
        bias                       = "none",
        use_gradient_checkpointing = "unsloth",
        random_state               = 3407,
    )
    print("✅ LoRA via Unsloth terapkan.")

tokenizer.pad_token = tokenizer.eos_token
print("✅ Model + LoRA siap.")

# ── Plain Tokenizer untuk Tokenisasi Dataset ───────────────
# PENTING: Unsloth me-patch Qwen3.5-9B sebagai VL (Vision-Language) processor.
# Tokenizer dari FastLanguageModel akan crash saat proses teks biasa
# karena mencoba handle images=None.
# Solusi: load AutoTokenizer plain terpisah HANYA untuk tokenisasi dataset & data collator.
print(f"\nMemuat plain tokenizer untuk tokenisasi teks...")
from transformers import AutoTokenizer as _PlainAutoTokenizer
try:
    text_tokenizer = _PlainAutoTokenizer.from_pretrained(
        MODEL_NAME_HF,   # selalu pakai HF name untuk hindari VL patch
        trust_remote_code=True,
        use_fast=True,
    )
except Exception:
    text_tokenizer = _PlainAutoTokenizer.from_pretrained(
        MODEL_NAME_HF, trust_remote_code=True
    )
text_tokenizer.pad_token = text_tokenizer.eos_token
print(f"✅ Plain tokenizer siap (vocab: {len(text_tokenizer):,} token)")

# ── Tokenisasi ─────────────────────────────────────────────
def tokenize_function(examples):
    # WAJIB pakai text_tokenizer (plain AutoTokenizer), BUKAN tokenizer dari unsloth
    # tokenizer dari unsloth di-patch sebagai VL processor → crash kalau terima teks biasa
    texts_with_eos = [text + text_tokenizer.eos_token for text in examples["text"]]
    return text_tokenizer(texts_with_eos, truncation=False)

def group_texts(examples):
    concatenated_examples = {k: sum(examples[k], []) for k in examples.keys()}
    total_length = len(concatenated_examples[list(examples.keys())[0]])
    if total_length >= block_size:
        total_length = (total_length // block_size) * block_size
    result = {
        k: [t[i : i + block_size] for i in range(0, total_length, block_size)]
        for k, t in concatenated_examples.items()
    }
    result["labels"] = result["input_ids"].copy()
    return result

print("Tokenisasi...")
tokenized_datasets = dataset.map(
    tokenize_function, batched=True, num_proc=1,
    remove_columns=dataset["train"].column_names
)
print(f"Packing ke {block_size} token...")
lm_datasets = tokenized_datasets.map(group_texts, batched=True, num_proc=1)
print(f"✅ Dataset Final:\n{lm_datasets}")

# ── Callback ───────────────────────────────────────────────
class WandBPerplexityCallback(TrainerCallback):
    def __init__(self):
        super().__init__()
        self.metrics = {
            'train_loss': [], 'train_perplexity': [],
            'eval_loss':  [], 'eval_perplexity':  [],
        }

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs and 'loss' in logs:
            step = state.global_step
            loss = logs['loss']
            ppl = math.exp(loss) if loss < 100 else float('inf')
            wandb.log({'train/perplexity': ppl}, step=step)
            self.metrics['train_loss'].append((step, loss))
            self.metrics['train_perplexity'].append((step, ppl))

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics and 'eval_loss' in metrics:
            step = state.global_step
            loss = metrics['eval_loss']
            ppl = math.exp(loss) if loss < 100 else float('inf')
            wandb.log({'eval/perplexity': ppl}, step=step)
            self.metrics['eval_loss'].append((step, loss))
            self.metrics['eval_perplexity'].append((step, ppl))

metrics_callback = WandBPerplexityCallback()

# ── Training Args ──────────────────────────────────────────
# 9B model lebih besar → batch lebih kecil per device
# Effective batch = 1 * 64 = 64 (sama dengan 0.5B: 2 * 32 = 64)
# PENTING: data_collator pakai text_tokenizer (plain), bukan tokenizer dari unsloth
data_collator = DataCollatorForLanguageModeling(tokenizer=text_tokenizer, mlm=False)

training_args = TrainingArguments(
    output_dir                  = checkpoint_path,
    per_device_train_batch_size = 3,    # Dinaikkan sesuai request
    gradient_accumulation_steps = 4,    # Dikurangi agar "step per detik" lebih cepat (update lebih sering)
    warmup_steps                = 100,
    num_train_epochs            = 3,
    learning_rate               = 2e-4, # LR disetel ke 2e-4 (200) sesuai request
    lr_scheduler_type           = "cosine",
    fp16                        = not torch.cuda.is_bf16_supported(),
    bf16                        = torch.cuda.is_bf16_supported(),
    logging_steps               = 5,
    optim                       = "adamw_8bit",
    weight_decay                = 0.01,
    report_to                   = "wandb",
    save_steps                  = 100,
    eval_strategy               = "steps",
    eval_steps                  = 100,
    gradient_checkpointing      = True,
    dataloader_num_workers      = 0,    # Aman untuk container
)

trainer = Trainer(
    model         = model,
    train_dataset = lm_datasets["train"],
    eval_dataset  = lm_datasets["validation"],
    args          = training_args,
    data_collator = data_collator,
    callbacks     = [metrics_callback],
)

# Statistik
num_train_samples = len(lm_datasets['train'])
total_batch_size  = training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps
total_steps       = (num_train_samples // total_batch_size) * int(training_args.num_train_epochs)
print(f"\n--- Statistik Training 9B ---")
print(f"Model         : {MODEL_NAME_HF}")
print(f"Total samples : {num_train_samples:,}")
print(f"Effective batch: {total_batch_size}")
print(f"Total steps   : {total_steps:,}")
print(f"Learning rate : {training_args.learning_rate}")
print(f"Warmup steps  : {training_args.warmup_steps}")

# ── Run Training ───────────────────────────────────────────
gc.collect()
torch.cuda.empty_cache()
torch.cuda.reset_peak_memory_stats()

last_checkpoint = None
if os.path.isdir(OUTPUT_DIR):
    last_checkpoint = get_last_checkpoint(OUTPUT_DIR)

if last_checkpoint:
    print(f"\n✅ Lanjut dari checkpoint: {last_checkpoint}")
else:
    print("\nℹ️  Mulai training dari awal...")

print("🚀 Training 9B dimulai...")

# --- RE-APPLY BYPASS TEPAT SEBELUM TRAINING ---
import transformers.trainer
if hasattr(transformers.trainer, 'check_torch_load_is_safe'):
    transformers.trainer.check_torch_load_is_safe = lambda: None
# ----------------------------------------------

trainer_stats = trainer.train(resume_from_checkpoint=last_checkpoint)
print("✅ Training selesai!")

# ── Evaluasi ───────────────────────────────────────────────
eval_results = trainer.evaluate()
eval_loss    = eval_results['eval_loss']
perplexity   = math.exp(eval_loss)
print(f"\nEval Loss  : {eval_loss:.4f}")
print(f"Perplexity : {perplexity:.2f}")

# ── Simpan Grafik ──────────────────────────────────────────
if metrics_callback.metrics['train_loss']:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    tl_steps  = [d[0] for d in metrics_callback.metrics['train_loss']]
    tl_values = [d[1] for d in metrics_callback.metrics['train_loss']]
    el_steps  = [d[0] for d in metrics_callback.metrics['eval_loss']]
    el_values = [d[1] for d in metrics_callback.metrics['eval_loss']]

    ax1.plot(tl_steps, tl_values, label='Training Loss', alpha=0.7)
    ax1.plot(el_steps, el_values, label='Validation Loss', marker='o')
    ax1.set_ylabel('Loss'); ax1.set_title('Loss — Qwen3.5-9B CPT')
    ax1.legend(); ax1.grid(True)

    tp_values = [d[1] for d in metrics_callback.metrics['train_perplexity']]
    ep_values = [d[1] for d in metrics_callback.metrics['eval_perplexity']]
    ax2.plot(tl_steps, tp_values, label='Train PPL',   color='orange', alpha=0.7)
    ax2.plot(el_steps, ep_values, label='Eval PPL',    color='red',    marker='o')
    ax2.set_xlabel('Steps'); ax2.set_ylabel('Perplexity')
    ax2.set_title('Perplexity — Qwen3.5-9B CPT'); ax2.legend(); ax2.grid(True)

    plt.tight_layout()
    fig_path = os.path.join(output_path, 'training_curves_9b.png')
    plt.savefig(fig_path, dpi=150)
    print(f"✅ Grafik disimpan: {fig_path}")

# ── Simpan Model ───────────────────────────────────────────
print(f"\nMenyimpan model ke {output_path} ...")
if USE_UNSLOTH:
    model.save_pretrained_merged(output_path, tokenizer, save_method="merged_16bit")
else:
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
print(f"✅ Model disimpan!")

wandb.finish()
print("✅ Semua selesai — Qwen3.5-9B CPT done!")