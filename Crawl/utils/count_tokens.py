"""
count_tokens.py — Menghitung estimasi total token dari data_raw/
Menggunakan tokenizer Qwen2.5 (sama untuk semua varian 7B/9B/14B/72B)

Cara pakai:
    python count_tokens.py
atau jalankan dari luar folder:
    python Crawl/count_tokens.py
"""

import os
import sys
from pathlib import Path

# ─── Konfigurasi ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DATA_DIR   = SCRIPT_DIR / "data_raw"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"   # valid di HuggingFace (Qwen2.5 tidak punya varian 9B)

# ─── Load Tokenizer ───────────────────────────────────────────────────────────
print("[*] Loading tokenizer Qwen2.5 (butuh internet pertama kali)...")
try:
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    print("[OK] Tokenizer berhasil dimuat.\n")
except ImportError:
    print("[!] Library 'transformers' belum terinstall.")
    print("    Jalankan: pip install transformers")
    sys.exit(1)
except Exception as e:
    print(f"[!] Gagal load tokenizer: {e}")
    sys.exit(1)

# ─── Hitung Token ─────────────────────────────────────────────────────────────
total_tokens  = 0
total_files   = 0
total_skipped = 0
errors        = 0

files = list(DATA_DIR.glob("**/*.md")) + list(DATA_DIR.glob("**/*.json"))

if not files:
    print(f"[!] Tidak ada file .md/.json di {DATA_DIR}")
    sys.exit(1)

print(f"[*] Ditemukan {len(files):,} file. Mulai menghitung token...\n")

for i, filepath in enumerate(files, 1):
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            total_skipped += 1
            continue
        tokens = tokenizer.encode(text, add_special_tokens=False)
        total_tokens += len(tokens)
        total_files  += 1

        # Progress setiap 50 file
        if i % 50 == 0:
            print(f"    [{i}/{len(files)}] Token terhitung: {total_tokens:,}")

    except Exception as e:
        errors += 1

# ─── Hasil Akhir ──────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  HASIL HITUNGAN TOKEN DATA CRAWL")
print("="*55)
print(f"  File diproses     : {total_files:,} file")
print(f"  File dilewati     : {total_skipped:,} file (kosong)")
print(f"  Error pembacaan   : {errors:,} file")
print(f"  Total Token       : {total_tokens:,} token")
print(f"  Setara dengan     : ~{total_tokens / 1_000_000:.2f} Juta Token")
print(f"  Setara dengan     : ~{total_tokens / 1_000_000_000:.4f} Miliar Token")
print("="*55)
print(f"\n  Konteks Qwen2.5-9B: Context window = 128K token")
print(f"  Dataset ini setara ~{total_tokens / 128_000:.0f}x full context window.")

# Estimasi kebutuhan training
avg_tokens_per_file = total_tokens / total_files if total_files else 0
print(f"\n  Rata-rata per file : ~{avg_tokens_per_file:,.0f} token")
print("="*55)
