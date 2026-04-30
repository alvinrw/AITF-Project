import os
import gc
import math

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import torch

_original_torch_load = torch.load
def _hacked_torch_load(*args, **kwargs):
    kwargs.pop('weights_only', None)
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _hacked_torch_load

import wandb
import matplotlib
matplotlib.use('Agg')
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

import transformers.utils.import_utils
if hasattr(transformers.utils.import_utils, 'check_torch_load_is_safe'):
    transformers.utils.import_utils.check_torch_load_is_safe = lambda: None
    print("🔓 Bypass keamanan Transformers berhasil diaktifkan!")

print("✅ Library berhasil diimport.")
print(f"GPU : {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Tidak ada GPU'}")
print(f"VRAM: {round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)} GB" if torch.cuda.is_available() else "")

# ============================================================
# KONFIGURASI
# ============================================================

MODEL_NAME      = "Qwen/Qwen3-8B-Base"  # ✅ #1
max_seq_length  = 4096
block_size      = max_seq_length

HOME            = os.path.expanduser('~')
BASE_DIR        = os.path.join(HOME, 'MKN-1', 'Training_cpt_qwen8B_v2')                     
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, 'Dataset', f'processed_qwen3_8b_v2_chunk_{block_size}') 
checkpoint_path = os.path.join(BASE_DIR, 'checkpoints', 'qwen3_cpt_8b_v2')                    
output_path     = os.path.join(BASE_DIR, 'output', 'qwen3_cpt_8b_v2_final')                      
OUTPUT_DIR      = checkpoint_path

WANDB_PROJECT   = "AITF - CPT"
WANDB_RUN_NAME  = "Qwen3-8B-AITF-CPT-v2" 

# ============================================================

os.makedirs(checkpoint_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

# ── WandB ──────────────────────────────────────────────────
os.environ['WANDB_API_KEY'] = 'YOUR_WANDB_API_KEY_HERE'  # Masukkan WandB API Key Anda
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
    # ✅ #4 — Muat dataset dari HF Hub
    print("Memuat dataset dari Hugging Face Hub...")
    dataset_hf = load_dataset(
        "alvinrifky/Crawling-MKN_1",
        data_files="clean/data_training_mixed.jsonl"
    )
    raw_dataset = dataset_hf["train"]
    # Filter dataset: buang teks kosong (sesuai ipynb)
    raw_dataset = raw_dataset.filter(lambda x: x['text'] is not None and x['text'].strip() != '')
    print(f"✅ Total dokumen domain setelah cleaning: {len(raw_dataset):,}")

    # --- Mencegah Catastrophic Forgetting dengan Data Umum (Wikipedia) ---
    wiki_count = int(len(raw_dataset) * 0.20)  # 20% (sesuai ipynb)
    print(f"\nMengambil {wiki_count} baris dari Wikipedia Indonesia (20%)...")

    wiki_dataset = load_dataset(
        "wikimedia/wikipedia",
        "20231101.id",
        split=f"train[:{wiki_count}]"
    )

    columns_to_keep = ["text"]
    raw_dataset  = raw_dataset.select_columns(columns_to_keep)
    wiki_dataset = wiki_dataset.select_columns(columns_to_keep)

    print("Menggabungkan dan mengacak dataset (Domain + Wiki)...")
    mixed_dataset = concatenate_datasets([raw_dataset, wiki_dataset])
    raw_dataset   = mixed_dataset.shuffle(seed=42)
    print(f"Jumlah baris dataset final: {len(raw_dataset):,}")

    print("Memisahkan dataset 90% train, 5% val, 5% test...")
    split_dataset  = raw_dataset.train_test_split(test_size=0.1, seed=42)
    val_test_split = split_dataset['test'].train_test_split(test_size=0.5, seed=42)
    dataset = DatasetDict({
        'train':      split_dataset['train'],
        'validation': val_test_split['train'],
        'test':       val_test_split['test'],
    })
    print(dataset)

    # ── Tokenisasi ─────────────────────────────────────────────
    def tokenize_function(examples):
        # Tambahkan EOS token di akhir setiap teks agar model paham batas dokumen (sesuai ipynb)
        texts = [text + tokenizer.eos_token if not text.endswith(tokenizer.eos_token) else text for text in examples["text"]]
        return tokenizer(texts, truncation=False)

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

    print(f"\n💾 Menyimpan dataset hasil chunking ke {PROCESSED_DATA_DIR} ...")
    lm_datasets.save_to_disk(PROCESSED_DATA_DIR)
    print("✅ Penyimpanan selesai!")

# ── Load Model + LoRA ──────────────────────────────────────
print(f"\nMemuat model {MODEL_NAME} ...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name     = MODEL_NAME,
    max_seq_length = max_seq_length,
    load_in_4bit   = True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r                          = 16,
    target_modules             = ["q_proj", "k_proj", "v_proj", "o_proj",
                                   "gate_proj", "up_proj", "down_proj"],
    lora_alpha                 = 32,
    lora_dropout               = 0.05,
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
            ppl  = math.exp(loss) if loss < 100 else float('inf')
            wandb.log({'train/perplexity': ppl}, step=step)
            self.metrics['train_loss'].append((step, loss))
            self.metrics['train_perplexity'].append((step, ppl))

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics and 'eval_loss' in metrics:
            step = state.global_step
            loss = metrics['eval_loss']
            ppl  = math.exp(loss) if loss < 100 else float('inf')
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
    hub_model_id                = "alvinrifky/Qwen3-8B-AITF-CPT-v2", 
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

import transformers.trainer
if hasattr(transformers.trainer, 'check_torch_load_is_safe'):
    transformers.trainer.check_torch_load_is_safe = lambda: None
import transformers.utils.import_utils
if hasattr(transformers.utils.import_utils, 'check_torch_load_is_safe'):
    transformers.utils.import_utils.check_torch_load_is_safe = lambda: None

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

    ax1.plot(tl_steps, tl_values, label='Training Loss',   alpha=0.7)
    ax1.plot(el_steps, el_values, label='Validation Loss', marker='o')
    ax1.set_ylabel('Loss'); ax1.set_title('Loss'); ax1.legend(); ax1.grid(True)

    tp_values = [d[1] for d in metrics_callback.metrics['train_perplexity']]
    ep_values = [d[1] for d in metrics_callback.metrics['eval_perplexity']]
    ax2.plot(tl_steps, tp_values, label='Train PPL', color='orange', alpha=0.7)
    ax2.plot(el_steps, ep_values, label='Eval PPL',  color='red',    marker='o')
    ax2.set_xlabel('Steps'); ax2.set_ylabel('Perplexity')
    ax2.set_title('Perplexity'); ax2.legend(); ax2.grid(True)

    plt.tight_layout()
    fig_path = os.path.join(output_path, 'training_curves_v2.png')  # ✅ #5
    plt.savefig(fig_path, dpi=150)
    print(f"✅ Grafik disimpan: {fig_path}")

# ── Simpan Model ───────────────────────────────────────────
print(f"\nMenyimpan model ke {output_path} ...")
model.save_pretrained_merged(output_path, tokenizer, save_method="merged_16bit")
print(f"✅ Model disimpan lokal!")

hf_repo_id = "alvinrifky/Qwen3-8B-AITF-CPT-v2"  # ✅ #3 #5
print(f"\nMencoba push model ke Hugging Face Hub ({hf_repo_id})...")
try:
    model.push_to_hub_merged(hf_repo_id, tokenizer, save_method="merged_16bit")
    print("✅ Berhasil push ke Hugging Face Hub!")
except Exception as e:
    print(f"⚠️ Gagal push ke Hugging Face Hub: {e}")

wandb.finish()
print("✅ Semua selesai.")