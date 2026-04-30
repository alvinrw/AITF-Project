import torch
from unsloth import FastLanguageModel
from transformers import AutoTokenizer

# ===== CONFIG =====
BASE_MODEL   = "Qwen/Qwen3-8B-Base"
CHECKPOINT   = "./checkpoints/qwen3_cpt_8b_v1/checkpoint-700"  # Sesuaikan dengan lokasi checkpoint LoRA Anda
OUTPUT_PATH  = "./output/qwen3_cpt_8b_v1_cp700_merged"         # Lokasi penyimpanan model hasil merge

# ===== LOAD TOKENIZER =====
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

# ===== LOAD BASE MODEL =====
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name     = BASE_MODEL,
    max_seq_length = 4096,
    load_in_4bit   = True,
)

# ===== LOAD LORA (CP-700) =====
model = FastLanguageModel.from_pretrained(
    model_name     = CHECKPOINT,
    max_seq_length = 4096,
    load_in_4bit   = True,
)[0]

print("✅ Model + LoRA CP-700 berhasil dimuat")

# ===== MERGE & SAVE =====
model.save_pretrained_merged(
    OUTPUT_PATH,
    tokenizer,
    save_method="merged_16bit"
)

print(f"✅ Model merged disimpan di: {OUTPUT_PATH}")