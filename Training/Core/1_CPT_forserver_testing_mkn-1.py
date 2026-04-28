# Auto-generated Python script from Notebook
# Untuk dijalankan menggunakan nohup di server


# Reinstall PyTorch dengan CUDA 12.1 (kompatibel dengan driver CUDA 12.2 di server ini)
# %pip install "torch>=2.3" torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 -q  # Magic command dikomentari

# Core dependencies
# %pip install -U datasets sentencepiece -q  # Magic command dikomentari
# %pip install -U "transformers>=4.44.0" "accelerate>=0.34.0" "peft>=0.11.0" -q  # Magic command dikomentari
# %pip install -U "bitsandbytes>=0.43.0" wandb -q  # Magic command dikomentari

# Unsloth
# %pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" -q  # Magic command dikomentari
# %pip install --no-deps "xformers<0.0.29" "trl<0.13.0" -q  # Magic command dikomentari

import os
import sys
import subprocess

print("\n⚙️ [INIT] Memastikan 'torchao' dihapus permanen untuk menghindari bug torch.int1...")
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import gc
import math

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import torch
import wandb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from unsloth import FastLanguageModel
from datasets import load_dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    TrainerCallback,
)
from transformers.trainer_utils import get_last_checkpoint

print("✅ Semua library berhasil diimport.")
print(f"PyTorch  : {torch.__version__}")
print(f"CUDA OK  : {torch.cuda.is_available()}")
print(f"GPU      : {torch.cuda.get_device_name(0)}")
print(f"VRAM     : {round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)} GB")


# ============================================================
# KONFIGURASI UTAMA — ubah di sini
# ============================================================
MODEL_NAME      = "unsloth/Qwen2.5-0.5B"
max_seq_length  = 2048
block_size      = max_seq_length

# Path dataset — sesuaikan dengan lokasi file di server
HOME            = os.path.expanduser('~')
JSONL_FILE      = os.path.join(HOME, 'Testing', 'Data', 'data_training_cpt.jsonl')

# Path output
checkpoint_path = os.path.join(HOME, 'Testing', 'checkpoints', 'qwen_cpt_2_5_0_5b')
output_path     = os.path.join(HOME, 'Testing', 'output', 'qwen_cpt_2_5_0_5b_final')
OUTPUT_DIR      = checkpoint_path

# WandB
WANDB_PROJECT   = "AITF - CPT"
WANDB_RUN_NAME  = "Qwen2.5-0.5B-AITF-CPT-server"
# ============================================================

os.makedirs(checkpoint_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

print(f"Model       : {MODEL_NAME}")
print(f"Dataset     : {JSONL_FILE}")
print(f"Dataset ada : {os.path.exists(JSONL_FILE)}")
print(f"Checkpoint  : {checkpoint_path}")
print(f"Output      : {output_path}")
# Hugging Face Config (Tambahan)
HF_TOKEN        = "" # MASUKKAN TOKEN HUGGINGFACE KAMU DI SINI, pastikan token role-nya WRITE (hf_xxxxx)
REPO_ID         = "alvinrifky/Qwen2.5-0.5B-AITF-CPT" # Username dan Repo HF



from huggingface_hub import login
print('🔑 Login Hugging Face...')
if 'HF_TOKEN' in globals() and HF_TOKEN.startswith('hf_'):
    try:
        login(token=HF_TOKEN, add_to_git_credential=True)
        print('✅ HuggingFace berhasil login!')
    except Exception as e:
        print(f'❌ HF Login Gagal: {e}')
else:
    print('⚠️ Token Hugging Face tidak valid/belum diisi. Fitur push_to_hub akan diabaikan.')

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
    print(f"✅ WandB aktif")
    print(f"   URL: {wandb.run.url}")
except Exception as e:
    print(f"⚠️  WandB gagal: {e}")
    wandb.init(mode='disabled')


from datasets import concatenate_datasets, load_dataset
if not os.path.exists(JSONL_FILE):
    raise FileNotFoundError(
        f"❌ File tidak ditemukan: {JSONL_FILE}\n"
        f"   Pastikan file sudah diupload ke folder Data di server."
    )

print("Memuat dataset domain spesifik...")
domain_dataset = load_dataset('json', data_files=JSONL_FILE, split='train')

print(f"\nMemuat dataset general (Wikipedia) untuk mencegah Catastrophic Forgetting...")
# Set rasio perbandingan misal 4:1 (Wikipedia ukuran = 25% dari dataset utama)
general_size = len(domain_dataset) // 4
try:
    general_dataset = load_dataset('wikimedia/wikipedia', '20231101.id', split=f'train[:{general_size}]')
except Exception as e:
    raise RuntimeError(f"❌ Gagal mengunduh Wikipedia: {e}. \nProses ini WAJIB berhasil untuk mencegah catastrophic forgetting! Cek koneksi Anda lalu jalankan ulang.")

# Pastikan hanya menyimpan kolom yang diperlukan ('text')
domain_dataset = domain_dataset.select_columns(['text'])
if 'text' in general_dataset.column_names:
    general_dataset = general_dataset.select_columns(['text'])

print("Menggabungkan dataset dan melakukan shuffle...")
raw_dataset = concatenate_datasets([domain_dataset, general_dataset]).shuffle(seed=42)

print(f"✅ Total dokumen siap latih: {len(raw_dataset):,} (Domain: {len(domain_dataset):,} | General: {len(general_dataset):,})")
# Timpa raw_dataset yang lama dengan yang baru digabungkan



print("Memisahkan 90% train / 10% validasi ...")
split_dataset = raw_dataset.train_test_split(test_size=0.1, seed=42)
dataset = DatasetDict({
    'train':      split_dataset['train'],
    'validation': split_dataset['test'],
})
print(dataset)


tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

def tokenize_function(examples):
    texts = [t + tokenizer.eos_token for t in examples['text']]
    return tokenizer(texts, truncation=False)

def group_texts(examples):
    concatenated = {k: sum(examples[k], []) for k in examples.keys()}
    total = len(concatenated[list(examples.keys())[0]])
    total = (total // block_size) * block_size
    result = {
        k: [t[i : i + block_size] for i in range(0, total, block_size)]
        for k, t in concatenated.items()
    }
    result['labels'] = result['input_ids'].copy()
    return result

print("Tokenisasi ... (mungkin perlu beberapa menit)")
tokenized = dataset.map(
    tokenize_function, batched=True, num_proc=1,
    remove_columns=dataset['train'].column_names
)
print(f"Packing ke {block_size} token ...")
lm_datasets = tokenized.map(group_texts, batched=True, num_proc=1)
print(f"✅ Dataset siap:\n{lm_datasets}")


print(f"Memuat {MODEL_NAME} ...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name     = MODEL_NAME,
    max_seq_length = max_seq_length,
    load_in_4bit   = True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r                          = 16,
    target_modules             = ['q_proj', 'k_proj', 'v_proj', 'o_proj',
                                   'gate_proj', 'up_proj', 'down_proj'],
    lora_alpha                 = 16,
    lora_dropout               = 0,
    bias                       = 'none',
    use_gradient_checkpointing = 'unsloth',
    random_state               = 3407,
)
print(f"✅ Model siap dengan QLoRA 4-bit.")


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
print('✅ Callback siap.')


# Callback untuk upload Checkpoint ke Google Drive secara perlahan
import subprocess

class MultiHubDriveUploadCallback(TrainerCallback):
    def on_save(self, args, state, control, **kwargs):
        # Dipanggil secara otomatis setiap trainer nyimpan checkpoint
        checkpoint_dir = f"{args.output_dir}/checkpoint-{state.global_step}"
        print(f"\n📤 [Callback] Mengunggah checkpoint langkah {state.global_step} ke Google Drive...")
        try:
            # Panggil file upload drive eksternal yg modifikasinya sudah bisa handle argumen direktori
            subprocess.run(["python", "upload_model_drive.py", checkpoint_dir], check=False)
            print("✅ Upload batch Drive selesai")
        except Exception as e:
            print(f"⚠️ Gagal unggah ke Drive: {e}")

multi_callback = MultiHubDriveUploadCallback()

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

training_args = TrainingArguments(
    output_dir                  = checkpoint_path,
    per_device_train_batch_size = 4,   # A100 80GB bisa lebih besar
    gradient_accumulation_steps = 16,
    warmup_steps                = 100,
    num_train_epochs            = 1,
    learning_rate               = 1e-5,
    lr_scheduler_type           = 'cosine',
    fp16                        = not torch.cuda.is_bf16_supported(),
    bf16                        = torch.cuda.is_bf16_supported(),
    logging_steps               = 5,
    optim                       = 'adamw_8bit',
    weight_decay                = 0.01,
    report_to                   = 'wandb',
    save_steps                  = 100,
    eval_strategy               = 'steps',
    eval_steps                  = 100,
    gradient_checkpointing      = True,
    push_to_hub                 = True,
    hub_model_id                = REPO_ID if 'REPO_ID' in globals() else "model-cpt",
    hub_token                   = HF_TOKEN if 'HF_TOKEN' in globals() else None,
    hub_strategy                = 'every_save',
)

trainer = Trainer(
    model         = model,
    train_dataset = lm_datasets['train'],
    eval_dataset  = lm_datasets['validation'],
    args          = training_args,
    data_collator = data_collator,
    callbacks     = [metrics_callback, multi_callback],
)

n_samples     = len(lm_datasets['train'])
total_batch   = training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps
total_steps   = (n_samples // total_batch) * int(training_args.num_train_epochs)

print(f"--- Statistik Training ---")
print(f"GPU             : {torch.cuda.get_device_name(0)}")
print(f"Total samples   : {n_samples:,}")
print(f"Effective batch : {total_batch}")
print(f"Total steps     : {total_steps:,}")
print(f"Learning rate   : {training_args.learning_rate}")
print(f"\n✅ Trainer siap — jalankan sel berikutnya untuk mulai training.")


gc.collect()
torch.cuda.empty_cache()

last_checkpoint = None
if os.path.isdir(OUTPUT_DIR):
    last_checkpoint = get_last_checkpoint(OUTPUT_DIR)

if last_checkpoint:
    print(f"✅ Lanjut dari checkpoint: {last_checkpoint}")
else:
    print("ℹ️  Mulai dari awal...")

trainer_stats = trainer.train(resume_from_checkpoint=last_checkpoint)
print("\n✅ Training selesai!")


eval_results = trainer.evaluate()
eval_loss    = eval_results['eval_loss']
perplexity   = math.exp(eval_loss)
print(f"Eval Loss  : {eval_loss:.4f}")
print(f"Perplexity : {perplexity:.2f}")

if metrics_callback.metrics['train_loss']:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    tl_s = [d[0] for d in metrics_callback.metrics['train_loss']]
    tl_v = [d[1] for d in metrics_callback.metrics['train_loss']]
    el_s = [d[0] for d in metrics_callback.metrics['eval_loss']]
    el_v = [d[1] for d in metrics_callback.metrics['eval_loss']]

    ax1.plot(tl_s, tl_v, label='Train Loss', alpha=0.7)
    ax1.plot(el_s, el_v, label='Val Loss', marker='o')
    ax1.set_ylabel('Loss'); ax1.legend(); ax1.grid(True)

    tp_v = [d[1] for d in metrics_callback.metrics['train_perplexity']]
    ep_v = [d[1] for d in metrics_callback.metrics['eval_perplexity']]
    ax2.plot(tl_s, tp_v, label='Train PPL', color='orange', alpha=0.7)
    ax2.plot(el_s, ep_v, label='Val PPL',   color='red',    marker='o')
    ax2.set_xlabel('Steps'); ax2.set_ylabel('Perplexity'); ax2.legend(); ax2.grid(True)

    plt.tight_layout()
    fig_path = os.path.join(output_path, 'training_curves.png')
    plt.savefig(fig_path, dpi=150)
    plt.show()
    print(f"✅ Grafik disimpan: {fig_path}")


print(f"Menyimpan model ke {output_path} ...")
model.save_pretrained_merged(output_path, tokenizer, save_method='merged_16bit')
print(f"✅ Model disimpan!")

wandb.finish()
print("✅ WandB selesai. Training pipeline selesai semua!")

