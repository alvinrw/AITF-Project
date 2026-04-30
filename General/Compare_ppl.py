import os
import sys
import subprocess
import importlib
import math
import random
import time
import traceback
from typing import Optional

# ─────────────────────────────────────────────
# STEP 0: DIAGNOSIS & AUTO-FIX ENVIRONMENT
# ─────────────────────────────────────────────

def check_and_fix_environment():
    print("=" * 60)
    print("PEMERIKSAAN ENVIRONMENT")
    print("=" * 60)
    issues = []

    try:
        import torch
        print(f"[OK] PyTorch        : {torch.__version__}")
        print(f"[OK] CUDA tersedia  : {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"[OK] GPU            : {torch.cuda.get_device_name(0)}")
    except ImportError:
        issues.append("torch"); print("[!!] PyTorch TIDAK ditemukan")

    try:
        import transformers
        print(f"[OK] Transformers   : {transformers.__version__}")
        from transformers import AutoModelForCausalLM  # noqa
    except ImportError:
        issues.append("transformers"); print("[!!] Transformers TIDAK ditemukan")

    try:
        import datasets
        print(f"[OK] Datasets       : {datasets.__version__}")
    except ImportError:
        issues.append("datasets"); print("[!!] Datasets TIDAK ditemukan")

    if issues:
        if "torch" in issues:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cu118", "--quiet"])
        remaining = [p for p in issues if p != "torch"]
        if remaining:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *remaining, "--quiet"])
        importlib.invalidate_caches()

    import torch
    x = torch.tensor([1.0, 2.0]); _ = x.sum()
    print(f"\n[OK] PyTorch berfungsi normal")
    return torch


def setup_hf_token():
    token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
    if token:
        print(f"\n[OK] HF Token ditemukan dari environment variable")
        return token
    print("\n[INFO] HF Token tidak ditemukan (Qwen publik, biasanya tidak perlu)")
    return None


# ─────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────

# Path ke model CPT Anda (bisa diganti sesuai dengan lokasi penyimpanan model)
CPT_MODEL_PATH = os.path.abspath("./output/qwen3_cpt_8b_v1_final")

MODELS = [
    "Qwen/Qwen3-8B",
    CPT_MODEL_PATH,
]

MODEL_LABELS = {
    "Qwen/Qwen3-8B" : "Qwen3-8B (Base)",
    CPT_MODEL_PATH  : "Qwen3-8B (CPT-MKN1)",
}

SAMPLE_FRACTION = 0.01
WIKI_FRACTION   = 0.20
SEED            = 42
MAX_LENGTH      = 2048
STRIDE          = 512
RESULTS_FILE    = "perplexity_results.csv"
PLOT_FILE       = "perplexity_comparison.png"


# ─────────────────────────────────────────────
# 1. MUAT & SAMPEL DATASET
# ─────────────────────────────────────────────

def load_and_sample_dataset(
    domain_fraction: float = SAMPLE_FRACTION,
    wiki_fraction:   float = WIKI_FRACTION,
    seed:            int   = SEED,
) -> list:
    from datasets import load_dataset, concatenate_datasets

    print("\n" + "=" * 60)
    print("MEMUAT DATASET")
    print("=" * 60)

    print("\n[1/3] Memuat dataset domain...")
    # Mengunduh dataset target (domain spesifik) langsung dari Hugging Face Hub
    dataset_hf = load_dataset(
        "alvinrifky/Crawling-MKN_1",
        data_files="clean/data_training_mixed.jsonl"
    )
    split_name = list(dataset_hf.keys())[0]
    ds_domain  = dataset_hf[split_name]
    total      = len(ds_domain)
    print(f"      Total domain   : {total:,} baris")

    text_col = None
    for candidate in ("text", "content", "instruction", "input", "output"):
        if candidate in ds_domain.column_names:
            text_col = candidate; break
    if text_col is None:
        text_col = "__combined__"
        ds_domain = ds_domain.map(
            lambda row: {"__combined__": " ".join(str(v) for v in row.values())}
        )
    print(f"      Kolom teks     : '{text_col}'")

    random.seed(seed)
    # Mengambil sebagian kecil dari dataset domain agar evaluasi berjalan lebih cepat namun tetap representatif
    n_domain = max(1, int(total * domain_fraction))
    idx      = random.sample(range(total), n_domain)
    ds_domain_sampled = ds_domain.select(idx)
    if text_col != "text":
        ds_domain_sampled = ds_domain_sampled.rename_column(text_col, "text")
    ds_domain_sampled = ds_domain_sampled.select_columns(["text"])
    print(f"      Sampel domain  : {n_domain:,} baris")

    # Menghitung porsi tambahan dari Wikipedia untuk menguji General Knowledge (mendeteksi catastrophic forgetting)
    n_wiki = max(1, int(n_domain * wiki_fraction))
    print(f"\n[2/3] Memuat Wikipedia Indonesia ({n_wiki:,} baris)...")
    ds_wiki = load_dataset("wikimedia/wikipedia", "20231101.id", split=f"train[:{n_wiki}]")
    ds_wiki = ds_wiki.select_columns(["text"])
    print(f"      Baris Wikipedia : {len(ds_wiki):,}")

    # Menyatukan data domain dan Wikipedia, lalu mengacak barisnya agar evaluasi tidak bias ke satu topik saja
    print(f"\n[3/3] Menggabungkan dan mengacak dataset...")
    mixed_ds = concatenate_datasets([ds_domain_sampled, ds_wiki]).shuffle(seed=seed)
    texts = [row["text"] for row in mixed_ds
             if isinstance(row["text"], str) and len(row["text"].strip()) > 50]
    print(f"      Total teks siap : {len(texts):,}")
    return texts


# ─────────────────────────────────────────────
# 2. HITUNG PERPLEXITY (dengan NaN guard)
# ─────────────────────────────────────────────

def compute_perplexity(
    model_name: str,
    texts:      list,
    hf_token:   Optional[str],
    max_length: int = MAX_LENGTH,
    stride:     int = STRIDE,
) -> dict:
    # Fungsi ini menghitung nilai perplexity model menggunakan metode sliding window.
    # Semakin kecil angka perplexity, semakin baik model memahami teks yang diberikan.
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from tqdm import tqdm

    device   = "cuda" if torch.cuda.is_available() else "cpu"
    label    = MODEL_LABELS.get(model_name, model_name.split("/")[-1])
    is_local = os.path.isdir(model_name)

    result = {
        "model"        : model_name,
        "label"        : label,
        "perplexity"   : None,
        "n_texts"      : len(texts),
        "n_tokens"     : 0,
        "n_skip_chunks": 0,
        "time_sec"     : 0,
        "error"        : None,
    }

    print(f"\n{'='*60}")
    print(f"Model  : {label}")
    print(f"Path   : {model_name}")
    print(f"Device : {device}")
    print(f"{'='*60}")

    if is_local and not os.path.isdir(model_name):
        result["error"] = f"Folder tidak ditemukan: {model_name}"
        print(f"[SKIP] {result['error']}")
        return result

    t_start = time.time()

    try:
        print("[1/3] Memuat tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, token=hf_token, trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        print("[2/3] Memuat model...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            token=hf_token,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        if device == "cpu":
            model = model.to(device)
        model.eval()

        n_params = sum(p.numel() for p in model.parameters()) / 1e9
        print(f"[OK] Model dimuat ({n_params:.2f}B params, device={device})")

    except Exception as e:
        result["error"] = str(e).split("\n")[0]
        print(f"[ERROR] {result['error']}")
        traceback.print_exc()
        return result

    # ── Kalkulasi Perplexity dengan NaN / Inf guard ────────────────
    print("[3/3] Menghitung perplexity (sliding window + NaN guard)...")

    total_nll    = 0.0
    total_tokens = 0
    skip_chunks  = 0
    nan_warned   = False

    for text in tqdm(texts, desc=label[:30], unit="teks"):
        try:
            encodings = tokenizer(text, return_tensors="pt", truncation=False)
        except Exception:
            continue

        input_ids = encodings.input_ids[0]
        seq_len   = len(input_ids)
        if seq_len < 2:
            continue

        prev_end = 0
        for begin in range(0, seq_len, stride):
            end        = min(begin + max_length, seq_len)
            chunk      = input_ids[begin:end].unsqueeze(0).to(device)
            target_len = end - prev_end
            labels     = chunk.clone()
            labels[0, :-target_len] = -100

            try:
                with torch.no_grad():
                    outputs = model(chunk, labels=labels)
                    nll     = outputs.loss.item()
            except Exception as e:
                skip_chunks += 1
                prev_end = end
                if end == seq_len:
                    break
                continue

            # ── NaN / Inf guard ────────────────────────────────────
            if not math.isfinite(nll) or nll < 0:
                skip_chunks += 1
                if not nan_warned:
                    print(f"\n[WARN] Loss tidak valid ({nll}) di chunk — akan di-skip. "
                          f"(Ini normal jika jarang terjadi)")
                    nan_warned = True
                prev_end = end
                if end == seq_len:
                    break
                continue

            # Clamp NLL ekstrem (misal karena token OOV atau teks rusak)
            # Batas atas: ln(vocab_size) * 2, biasanya ~20 untuk LLM modern
            nll = min(nll, 20.0)

            total_nll    += nll * target_len
            total_tokens += target_len
            prev_end = end

            if end == seq_len:
                break

    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print(f"\n[DEBUG] total_nll    = {total_nll:.2f}")
    print(f"[DEBUG] total_tokens = {total_tokens:,}")
    print(f"[DEBUG] skip_chunks  = {skip_chunks:,}")

    if total_tokens == 0:
        result["error"] = "total_tokens = 0, semua chunk di-skip (kemungkinan model corrupt)"
        print(f"[ERROR] {result['error']}")
        return result

    avg_nll    = total_nll / total_tokens
    perplexity = math.exp(avg_nll)
    elapsed    = time.time() - t_start

    result.update({
        "perplexity"   : round(perplexity, 4),
        "n_tokens"     : total_tokens,
        "n_skip_chunks": skip_chunks,
        "time_sec"     : round(elapsed, 1),
    })

    print(f"\n[HASIL] avg NLL     : {avg_nll:.6f}")
    print(f"[HASIL] Perplexity  : {perplexity:.4f}")
    print(f"[INFO]  Token       : {total_tokens:,}")
    print(f"[INFO]  Skip chunks : {skip_chunks:,}")
    print(f"[INFO]  Waktu       : {elapsed/60:.1f} menit")
    return result


# ─────────────────────────────────────────────
# 3. VISUALISASI
# ─────────────────────────────────────────────

def plot_results(df, output_file: str = PLOT_FILE):
    # Membuat visualisasi perbandingan model dalam bentuk grafik batang (bar chart)
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import matplotlib.patches as mpatches

    df_plot = df[df["perplexity"].notna()].copy()
    if df_plot.empty:
        print("[WARN] Tidak ada hasil valid untuk divisualisasikan.")
        return

    df_plot = df_plot.sort_values("perplexity")
    labels  = df_plot["label"].tolist()
    values  = df_plot["perplexity"].tolist()

    colors = ["#2ecc71" if "CPT" in lbl else "#3498db" for lbl in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(labels, values, color=colors, edgecolor="white", height=0.45)
    for bar, val in zip(bars, values):
        ax.text(val + max(values)*0.01, bar.get_y() + bar.get_height()/2,
                f"{val:,.2f}", va="center", fontsize=12, fontweight="bold")

    ax.set_xlabel("Perplexity (lebih rendah = lebih baik)", fontsize=12)
    ax.set_title(
        "Perbandingan Perplexity: Qwen3-8B Base vs CPT-MKN1\n"
        "(Dataset: 5% domain + 20% Wikipedia Indonesia, di-shuffle)",
        fontsize=13, fontweight="bold"
    )
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    patch_base = mpatches.Patch(color="#3498db", label="Base model (HuggingFace)")
    patch_cpt  = mpatches.Patch(color="#2ecc71", label="CPT model (hasil training)")
    ax.legend(handles=[patch_base, patch_cpt], loc="lower right", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"\n[INFO] Grafik disimpan → {output_file}")


# ─────────────────────────────────────────────
# 4. MAIN
# ─────────────────────────────────────────────

def main():
    import pandas as pd

    check_and_fix_environment()
    hf_token = setup_hf_token()

    print("\n" + "=" * 60)
    print("VALIDASI PATH MODEL CPT")
    print("=" * 60)
    if os.path.isdir(CPT_MODEL_PATH):
        cpt_files = os.listdir(CPT_MODEL_PATH)
        print(f"[OK] Folder CPT ditemukan")
        print(f"[OK] Isi: {cpt_files[:8]}{'...' if len(cpt_files)>8 else ''}")
    else:
        print(f"[ERROR] Folder CPT tidak ditemukan: {CPT_MODEL_PATH}")
        sys.exit(1)

    texts = load_and_sample_dataset()

    results = []
    for model_name in MODELS:
        res = compute_perplexity(model_name, texts, hf_token=hf_token)
        results.append(res)
        pd.DataFrame(results).to_csv(RESULTS_FILE, index=False)
        print(f"[INFO] Progress tersimpan → {RESULTS_FILE}")

    df = pd.DataFrame(results)
    print("\n" + "=" * 60)
    print("RINGKASAN HASIL PERPLEXITY")
    print("=" * 60)

    valid = df[df["perplexity"].notna()].sort_values("perplexity").copy()
    if not valid.empty:
        print(valid[["label", "perplexity", "n_tokens", "n_skip_chunks", "time_sec"]].to_string(index=False))
        best = valid.iloc[0]
        print(f"\n🏆 Model terbaik  : {best['label']}  →  PPL = {best['perplexity']:,.4f}")
        if len(valid) == 2:
            worst = valid.iloc[-1]
            diff  = worst["perplexity"] - best["perplexity"]
            pct   = (diff / worst["perplexity"]) * 100
            print(f"📉 Selisih PPL    : {diff:,.4f}  ({pct:.1f}% lebih rendah)")
            if "CPT" in best["label"]:
                print("✅ CPT model LEBIH BAIK dari base model pada dataset ini!")
            else:
                print("⚠️  Base model masih lebih baik — CPT perlu iterasi lebih lanjut.")
    else:
        print("Tidak ada model yang berhasil dievaluasi.")

    failed = df[df["error"].notna()]
    if not failed.empty:
        print("\n⚠️  Model yang gagal:")
        for _, row in failed.iterrows():
            print(f"   • {row['label']}: {str(row['error'])[:120]}")

    df.to_csv(RESULTS_FILE, index=False)
    print(f"\n[INFO] Hasil final → {RESULTS_FILE}")
    plot_results(df)


if __name__ == "__main__":
    main()