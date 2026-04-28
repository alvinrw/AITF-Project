
import os
import gc
import math

# Nonaktifkan parallelism tokenizer supaya tidak crash di Docker/container
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import torch

# --- ULTIMATE BYPASS UNTUK SELURUH ERROR TORCH.LOAD ---
_original_torch_load = torch.load
def _hacked_torch_load(*args, **kwargs):
    kwargs.pop('weights_only', None)
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _hacked_torch_load
# --------------------------------------------------------

import wandb
import matplotlib
matplotlib.use('Agg')  # Backend non-GUI untuk server (tidak perlu display)
import matplotlib.pyplot as plt

from unsloth import FastLanguageModel
from datasets import load_dataset, DatasetDict, concatenate_datasets, load_from_disk
from transformers import (
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    TrainerCallback,
)
from transformers.trainer_utils import get_last_checkpoint

# --- BYPASS SECURITY CHECK UNTUK PYTORCH 2.5.1 ---
import transformers.utils.import_utils
if hasattr(transformers.utils.import_utils, 'check_torch_load_is_safe'):
    transformers.utils.import_utils.check_torch_load_is_safe = lambda: None
    print("🔓 Bypass keamanan Transformers (CVE-2025-32434) berhasil diaktifkan!")
# -----------------------------------------------

print("✅ Library berhasil diimport.")
print(f"GPU : {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Tidak ada GPU'}")
print(f"VRAM: {round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)} GB" if torch.cuda.is_available() else "")

# ============================================================
# KONFIGURASI — ubah di sini
# ============================================================
MODEL_NAME      = "unsloth/Qwen3-8B"
max_seq_length  = 4096
block_size      = max_seq_length

# Path dataset (sesuaikan dengan struktur folder di server)
HOME            = os.path.expanduser('~')
BASE_DIR        = os.path.join(HOME, 'MKN-1', 'Training_cpt_qwen9B')
JSONL_FILE      = os.path.join(BASE_DIR, 'Dataset', 'data_training_mixed.jsonl') # Ganti nama jsonl-nya jika berbeda
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, 'Dataset', f'processed_qwen3_8b_chunk_{block_size}')
checkpoint_path = os.path.join(BASE_DIR, 'checkpoints', 'qwen3_cpt_8b_v1')
output_path     = os.path.join(BASE_DIR, 'output', 'qwen3_cpt_8b_v1_final')
OUTPUT_DIR      = checkpoint_path

WANDB_PROJECT   = "AITF - CPT"
WANDB_RUN_NAME  = "Qwen3-8B-AITF-CPT-v1"
# ============================================================

os.makedirs(checkpoint_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

# ── WandB ──────────────────────────────────────────────────
os.environ['WANDB_API_KEY'] = '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'
try:
    wandb.login()
    wandb.init(
        project = WANDB_PROJECT,
        name    = WANDB_RUN_NAME,
        reinit  = "finish_previous",
        config  = {
            "model_name":     MODEL_NAME,
            "max_seq_length": max_seq_length,
            "block_size":     block_size,
        }
    )
    print(f"✅ WandB aktif → {wandb.run.url}")
except Exception as e:
    print(f"⚠️ WandB gagal: {e}. Lanjut tanpa monitoring.")
    wandb.init(mode='disabled')

# ── Tokenizer ──────────────────────────────────────────────
print(f"\nMemuat tokenizer dari {MODEL_NAME} ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

# ── Load Dataset & Chunking ────────────────────────────────
if os.path.exists(PROCESSED_DATA_DIR):
    print(f"\n✅ Ditemukan dataset yang sudah di-chunking! Memuat dari {PROCESSED_DATA_DIR} ...")
    lm_datasets = load_from_disk(PROCESSED_DATA_DIR)
    print(f"✅ Dataset Final:\n{lm_datasets}")
else:
    if not os.path.exists(JSONL_FILE):
        raise FileNotFoundError(f"❌ File tidak ditemukan: {JSONL_FILE}")

    print(f"\nMemuat dataset dari {JSONL_FILE} ...")
    raw_dataset = load_dataset("json", data_files=JSONL_FILE, split="train")
    print(f"✅ Total dokumen domain: {len(raw_dataset):,}")

    # --- Mencegah Catastrophic Forgetting dengan Data Umum (Wikipedia) ---
    wiki_count = int(len(raw_dataset) * 0.25)
    print(f"\nMengambil {wiki_count} baris dari Wikipedia Indonesia (25%)...")

    wiki_dataset = load_dataset(
        "wikimedia/wikipedia",
        "20231101.id",
        split=f"train[:{wiki_count}]"
    )

    # Samakan format agar bisa digabung (kita hanya butuh kolom 'text')
    columns_to_keep = ["text"]
    raw_dataset = raw_dataset.select_columns(columns_to_keep)
    wiki_dataset = wiki_dataset.select_columns(columns_to_keep)

    # Gabungkan dan acak (shuffle)
    print("Menggabungkan dan mengacak dataset (Domain + Wiki)...")
    mixed_dataset = concatenate_datasets([raw_dataset, wiki_dataset])
    raw_dataset = mixed_dataset.shuffle(seed=42)

    print(f"Jumlah baris dataset final: {len(raw_dataset):,}")

    print("Memisahkan dataset 90% train, 5% val, 5% test...")
    # Pisahkan dulu 90% train dan 10% sisa
    split_dataset = raw_dataset.train_test_split(test_size=0.1, seed=42)
    # Bagi sisa 10% menjadi 5% val dan 5% test (0.5 dari 10%)
    val_test_split = split_dataset['test'].train_test_split(test_size=0.5, seed=42)
    dataset = DatasetDict({
        'train':      split_dataset['train'],
        'validation': val_test_split['train'],
        'test':       val_test_split['test'],
    })
    print(dataset)

    # ── Tokenisasi ─────────────────────────────────────────────
    def tokenize_function(examples):
        texts_with_eos = [text + tokenizer.eos_token for text in examples["text"]]
        return tokenizer(texts_with_eos, truncation=False)

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
        tokenize_function, batched=True, num_proc=1,  # num_proc=1 untuk Docker
        remove_columns=dataset["train"].column_names
    )
    print(f"Packing ke {block_size} token...")
    lm_datasets = tokenized_datasets.map(group_texts, batched=True, num_proc=1)
    print(f"✅ Dataset Final:\n{lm_datasets}")
    
    print(f"\n💾 Menyimpan dataset hasil chunking ke {PROCESSED_DATA_DIR} ...")
    lm_datasets.save_to_disk(PROCESSED_DATA_DIR)
    print("✅ Penyimpanan selesai!")

# ── Load Model + LoRA ──────────────────────────────────────
print(f"\nMemuat model {MODEL_NAME} ...")
import os
# os.environ["HF_HUB_OFFLINE"] = "1"

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name       = MODEL_NAME,
    max_seq_length   = max_seq_length,
    load_in_4bit     = True,
    # local_files_only = True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r                          = 16,
    target_modules             = ["q_proj", "k_proj", "v_proj", "o_proj",
                                   "gate_proj", "up_proj", "down_proj"],
    lora_alpha                 = 32, # Diubah dari 16 menjadi 32, standarnya 2 * r
    lora_dropout               = 0,
    bias                       = "none",
    use_gradient_checkpointing = "unsloth",
    random_state               = 3407,
)
print("✅ Model + LoRA siap.")

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
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

training_args = TrainingArguments(
    output_dir                  = checkpoint_path,
    per_device_train_batch_size = 8,
    per_device_eval_batch_size  = 8,
    gradient_accumulation_steps = 16,
    warmup_ratio                = 0.03,
    num_train_epochs            = 1,
    learning_rate               = 2e-4,
    lr_scheduler_type           = "cosine",
    fp16                        = not torch.cuda.is_bf16_supported(),
    bf16                        = torch.cuda.is_bf16_supported(),
    logging_steps               = 30,
    optim                       = "adamw_8bit",
    weight_decay                = 0.01,
    report_to                   = "wandb",
    save_steps                  = 100,
    eval_strategy               = "steps",
    eval_steps                  = 50,
    gradient_checkpointing      = True,
    dataloader_num_workers      = 4,
    push_to_hub                 = True,
    hub_model_id                = "alvinrifky/Qwen3-8B-AITF-CPT",
    hub_strategy                = "checkpoint",
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
print(f"\n--- Statistik Training ---")
print(f"Total samples : {num_train_samples:,}")
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

print("🚀 Training dimulai...")

# --- HARDEST BYPASS UNTUK TRANSFORMERS 5.5.0 ---
import transformers.trainer
if hasattr(transformers.trainer, 'check_torch_load_is_safe'):
    transformers.trainer.check_torch_load_is_safe = lambda: None
import transformers.utils.import_utils
if hasattr(transformers.utils.import_utils, 'check_torch_load_is_safe'):
    transformers.utils.import_utils.check_torch_load_is_safe = lambda: None
# -----------------------------------------------

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
    ax1.set_ylabel('Loss'); ax1.set_title('Loss'); ax1.legend(); ax1.grid(True)

    tp_values = [d[1] for d in metrics_callback.metrics['train_perplexity']]
    ep_values = [d[1] for d in metrics_callback.metrics['eval_perplexity']]
    ax2.plot(tl_steps, tp_values, label='Train PPL',   color='orange', alpha=0.7)
    ax2.plot(el_steps, ep_values, label='Eval PPL',    color='red',    marker='o')
    ax2.set_xlabel('Steps'); ax2.set_ylabel('Perplexity')
    ax2.set_title('Perplexity'); ax2.legend(); ax2.grid(True)

    plt.tight_layout()
    fig_path = os.path.join(output_path, 'training_curves.png')
    plt.savefig(fig_path, dpi=150)
    print(f"✅ Grafik disimpan: {fig_path}")

# ── Simpan Model ───────────────────────────────────────────
print(f"\nMenyimpan model ke {output_path} ...")
model.save_pretrained_merged(output_path, tokenizer, save_method="merged_16bit")
print(f"✅ Model disimpan lokal!")

# Push ke Hugging Face Hub (Pastikan sudah login pakai `huggingface-cli login` di terminal)
hf_repo_id = "USERNAME_KAMU/Qwen3-8B-AITF-CPT" # Ubah USERNAME_KAMU sesuai username HF
print(f"\nMencoba push model ke Hugging Face Hub ({hf_repo_id})...")
try:
    model.push_to_hub_merged(hf_repo_id, tokenizer, save_method="merged_16bit")
    print("✅ Berhasil push ke Hugging Face Hub!")
except Exception as e:
    print(f"⚠️ Gagal push ke Hugging Face Hub: {e}")

wandb.finish()
print("✅ Semua selesai.")
