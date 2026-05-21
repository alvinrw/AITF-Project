import os
import sys
import subprocess
import importlib
import math
import random
import time
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
        issues.append("torch")
        print("[!!] PyTorch TIDAK ditemukan")

    try:
        import transformers
        print(f"[OK] Transformers   : {transformers.__version__}")
    except ImportError:
        issues.append("transformers")
        print("[!!] Transformers TIDAK ditemukan")

    try:
        import datasets
        print(f"[OK] Datasets       : {datasets.__version__}")
    except ImportError:
        issues.append("datasets")
        print("[!!] Datasets TIDAK ditemukan")

    try:
        import accelerate
        print(f"[OK] Accelerate     : {accelerate.__version__}")
    except ImportError:
        issues.append("accelerate")
        print("[WARN] Accelerate tidak ditemukan — direkomendasikan untuk Trainer")

    if issues:
        print(f"\n[INFO] Menginstall paket yang kurang: {issues}")
        if "torch" in issues:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cu118", "--quiet"
            ])
        remaining = [p for p in issues if p != "torch"]
        if remaining:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *remaining, "--quiet"])
        importlib.invalidate_caches()

    try:
        import torch
        _ = torch.tensor([1.0, 2.0]).sum()
        print(f"\n[OK] PyTorch berfungsi normal")
        return torch
    except Exception as e:
        print(f"\n[FATAL] PyTorch masih bermasalah: {e}")
        sys.exit(1)


def setup_hf_token() -> Optional[str]:
    token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")

    # Kalau token ada di environment
    if token:
        print(f"\n[OK] HF Token ditemukan dari environment variable")
        return token

    print("\n" + "=" * 60)
    print("HUGGING FACE TOKEN")
    print("=" * 60)
    print("Model LLaMA memerlukan autentikasi.")
    print("Dapatkan token di: https://huggingface.co/settings/tokens\n")

    # Cek apakah terminal interactive
    if not sys.stdin.isatty():
        print("[INFO] Non-interactive mode terdeteksi (nohup/screen).")
        print("[INFO] Tanpa token — model LLaMA akan dilewati")
        return None

    try:
        token = input("Masukkan HF Token (kosongkan untuk skip model LLaMA): ").strip()
    except (EOFError, KeyboardInterrupt, OSError):
        token = ""

    if token:
        os.environ["HUGGINGFACE_TOKEN"] = token

        try:
            from huggingface_hub import login

            login(token=token, add_to_git_credential=False)
            print("[OK] Login HuggingFace berhasil")

        except Exception as e:
            print(f"[WARN] huggingface_hub login gagal: {e}")

    else:
        print("[INFO] Tanpa token — model LLaMA akan dilewati")

    return token or None
# ─────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────
MODELS = [
    "meta-llama/Meta-Llama-3-8B",
    "meta-llama/Llama-3.1-8B",
    "Qwen/Qwen3.5-9B-Base",
    "Qwen/Qwen3-8B-Base",
    "google/gemma-3-12b",
    "mistralai/Mistral-7B-v0.3",
]

SEED                   = 42
MAX_LENGTH             = 2048          # panjang tiap chunk (token)
MIN_CHUNK_TOKENS       = 32            # chunk lebih pendek dari ini dibuang
MAIN_SAMPLE_FRACTION   = 0.02          # ambil 2% dari dataset utama
WIKI_RATIO             = 0.20          # wiki = 20% dari jumlah main sample
PER_DEVICE_EVAL_BATCH  = 4
LATENCY_WARMUP_RUNS    = 2
LATENCY_BENCH_RUNS     = 5
LATENCY_GEN_TOKENS     = 128
RESULTS_FILE           = "perplexityV3_results.csv"
PLOT_FILE              = "perplexityV3_comparison.png"


# ─────────────────────────────────────────────
# 1. LOAD & SIAPKAN DATASET
# ─────────────────────────────────────────────
def load_eval_texts(seed: int = SEED) -> list[str]:
    from datasets import load_dataset

    # ── Main dataset ─────────────────────────────────────────
    print("=" * 60)
    print("LOAD MAIN DATASET")
    print("=" * 60)

    main_ds = load_dataset(
        "alvinrifky/Crawling-MKN_1",
        data_files="clean/data_training_mixed.jsonl"
    )
    split_name = list(main_ds.keys())[0]
    main_ds    = main_ds[split_name]
    print(f"[INFO] Total dataset : {len(main_ds):,}")

    TEXT_COL = None
    for c in ["text", "content", "instruction", "input", "output"]:
        if c in main_ds.column_names:
            TEXT_COL = c
            break
    if TEXT_COL is None:
        raise ValueError("No text column found!")
    print(f"[INFO] Text column   : {TEXT_COL}")

    # Sample 2% dari main dataset
    random.seed(seed)
    n_main   = max(1, int(len(main_ds) * MAIN_SAMPLE_FRACTION))
    indices  = random.sample(range(len(main_ds)), n_main)
    main_texts = [
        main_ds[idx][TEXT_COL]
        for idx in indices
        if isinstance(main_ds[idx][TEXT_COL], str) and main_ds[idx][TEXT_COL].strip()
    ]
    print(f"[INFO] Main sampled  : {len(main_texts):,}")

    # ── WikiText-2 ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("LOAD WIKITEXT")
    print("=" * 60)

    wiki_ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    wiki_texts = [
        row["text"]
        for row in wiki_ds
        if isinstance(row["text"], str) and len(row["text"].strip()) > 20
    ]
    print(f"[INFO] Wiki rows     : {len(wiki_texts):,}")

    # Ambil 20% dari jumlah main sample
    wiki_take  = int(len(main_texts) * WIKI_RATIO)
    wiki_texts = random.sample(wiki_texts, min(wiki_take, len(wiki_texts)))
    print(f"[INFO] Wiki sampled  : {len(wiki_texts):,}")

    # ── Gabung + shuffle ─────────────────────────────────────
    all_texts = main_texts + wiki_texts
    random.seed(seed)
    random.shuffle(all_texts)
    print(f"\n[INFO] Final eval samples : {len(all_texts):,}  "
          f"(main={len(main_texts):,} + wiki={len(wiki_texts):,})")

    return all_texts


# ─────────────────────────────────────────────
# 2. TOKENISASI + CHUNKING (fixed size, no overlap)
# ─────────────────────────────────────────────
def build_eval_dataset(texts: list[str], tokenizer, max_length: int, min_chunk: int):
    """
    Tokenisasi semua teks, potong menjadi chunk fixed MAX_LENGTH token
    (tidak ada overlap/stride). Chunk terlalu pendek dibuang.
    """
    from datasets import Dataset

    all_input_ids  = []
    skipped_chunks = 0

    for text in texts:
        enc = tokenizer(text, return_tensors="pt", truncation=False)
        ids = enc.input_ids[0].tolist()

        # potong fixed, tanpa overlap
        for i in range(0, len(ids), max_length):
            chunk = ids[i : i + max_length]
            if len(chunk) < min_chunk:
                skipped_chunks += 1
                continue
            all_input_ids.append(chunk)

    print(f"[INFO] Total chunks  : {len(all_input_ids):,}  "
          f"(dibuang terlalu pendek: {skipped_chunks})")

    return Dataset.from_dict({"input_ids": all_input_ids})


# ─────────────────────────────────────────────
# 3. BENCHMARK: LATENCY, THROUGHPUT, VRAM
# ─────────────────────────────────────────────
def benchmark_latency_throughput(
    model,
    tokenizer,
    device: str,
    prompt: str      = "Apa itu kecerdasan buatan?",
    warmup_runs: int = LATENCY_WARMUP_RUNS,
    bench_runs: int  = LATENCY_BENCH_RUNS,
    gen_tokens: int  = LATENCY_GEN_TOKENS,
) -> dict:
    import torch

    inputs    = tokenizer(prompt, return_tensors="pt").to(device)
    input_len = inputs["input_ids"].shape[-1]

    # Warmup
    with torch.no_grad():
        for _ in range(warmup_runs):
            model.generate(
                **inputs,
                max_new_tokens=gen_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
    if device == "cuda":
        torch.cuda.synchronize()

    # Benchmark
    latencies, tokens_generated = [], []
    with torch.no_grad():
        for _ in range(bench_runs):
            t0  = time.perf_counter()
            out = model.generate(
                **inputs,
                max_new_tokens=gen_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
            if device == "cuda":
                torch.cuda.synchronize()
            t1 = time.perf_counter()

            latencies.append(t1 - t0)
            tokens_generated.append(out.shape[-1] - input_len)

    avg_latency    = sum(latencies) / len(latencies)
    avg_tok        = sum(tokens_generated) / len(tokens_generated)
    return {
        "latency_sec"     : round(avg_latency, 3),
        "throughput_tok_s": round(avg_tok / avg_latency, 2),
    }


# ─────────────────────────────────────────────
# 4. HITUNG PERPLEXITY + SEMUA METRIK
#
#    PPL = exp(eval_loss)
#    eval_loss = mean cross-entropy atas semua token
#    (dihitung oleh HuggingFace Trainer, bukan rumus custom)
# ─────────────────────────────────────────────
def compute_perplexity(
    model_name : str,
    texts      : list[str],
    hf_token   : Optional[str],
    max_length : int = MAX_LENGTH,
) -> dict:
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"

    result = {
        "model"           : model_name,
        "params_B"        : None,
        "perplexity"      : None,
        "latency_sec"     : None,
        "throughput_tok_s": None,
        "vram_GB"         : None,
        "n_texts"         : len(texts),
        "n_tokens"        : 0,
        "time_sec"        : 0,
        "error"           : None,
    }

    print(f"\n{'='*60}")
    print(f"Model  : {model_name}")
    print(f"Device : {device}")
    print(f"{'='*60}")

    is_gated = model_name.startswith("meta-llama/")
    if is_gated and not hf_token:
        result["error"] = "Model LLaMA memerlukan HF Token."
        print(f"[SKIP] {result['error']}")
        return result

    t_start = time.time()

    try:
        # ── [1/5] Tokenizer ──────────────────────────────────
        print("[1/5] Memuat tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, token=hf_token, trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # ── [2/5] Tokenisasi + chunking (fixed, no overlap) ──
        print("[2/5] Tokenisasi & chunking (fixed size, no overlap)...")
        eval_dataset = build_eval_dataset(
            texts, tokenizer,
            max_length=max_length,
            min_chunk=MIN_CHUNK_TOKENS,
        )
        total_tokens        = sum(len(x) for x in eval_dataset["input_ids"])
        result["n_tokens"]  = total_tokens
        print(f"[INFO] Total token   : {total_tokens:,}")

        # ── [3/5] Load model ─────────────────────────────────
        print("[3/5] Memuat model...")
        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()

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

        n_params_B        = sum(p.numel() for p in model.parameters()) / 1e9
        result["params_B"] = round(n_params_B, 3)
        print(f"[OK] Model dimuat ({n_params_B:.3f}B parameter)")

        # ── [4/5] Benchmark latency & throughput ─────────────
        print("[4/5] Benchmark latency & throughput...")
        bench = benchmark_latency_throughput(model, tokenizer, device)
        result["latency_sec"]       = bench["latency_sec"]
        result["throughput_tok_s"]  = bench["throughput_tok_s"]
        print(f"[OK] Latency         : {bench['latency_sec']:.3f} s")
        print(f"[OK] Throughput      : {bench['throughput_tok_s']:.2f} tok/s")

        # Peak VRAM setelah benchmark
        if device == "cuda":
            torch.cuda.synchronize()
            result["vram_GB"] = round(torch.cuda.max_memory_allocated() / 1024**3, 3)
            print(f"[OK] VRAM (peak)     : {result['vram_GB']:.3f} GB")

        # ── [5/5] Perplexity via Trainer ─────────────────────
        # Rumus: PPL = exp(eval_loss)
        #        eval_loss = rata-rata cross-entropy token
        #        (Trainer menghitung NLL per token, kita exp()-kan)
        print("[5/5] Evaluasi perplexity  [PPL = exp(eval_loss)] ...")

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
            pad_to_multiple_of=8 if device == "cuda" else None,
        )
        training_args = TrainingArguments(
            output_dir="./eval_tmp",
            per_device_eval_batch_size=PER_DEVICE_EVAL_BATCH,
            fp16=(device == "cuda"),
            dataloader_num_workers=2,
            report_to="none",
            log_level="error",
        )
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=None,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
        )

        eval_results = trainer.evaluate()
        eval_loss    = eval_results["eval_loss"]
        perplexity   = math.exp(eval_loss)         # PPL = e^(mean NLL)

    except Exception as e:
        result["error"] = str(e).split("\n")[0]
        print(f"[ERROR] {result['error']}")
        return result
    finally:
        try:
            del model
        except NameError:
            pass
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    elapsed = time.time() - t_start
    result.update({
        "perplexity": round(perplexity, 4),
        "time_sec"  : round(elapsed, 1),
    })

    print(f"\n[HASIL] Eval loss    : {eval_loss:.6f}")
    print(f"[HASIL] Perplexity   : {perplexity:.4f}  (= exp({eval_loss:.4f}))")
    print(f"[INFO]  Token total  : {total_tokens:,}")
    print(f"[INFO]  Waktu        : {elapsed/60:.1f} menit")
    return result


# ─────────────────────────────────────────────
# 5. VISUALISASI
# ─────────────────────────────────────────────
def plot_results(df, output_file: str = PLOT_FILE):
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    METRICS = [
        ("params_B",         "Params (B)",             "Blues",      True),
        ("perplexity",       "Perplexity ↓",           "RdYlGn_r",  False),
        ("latency_sec",      "Latency (s) ↓",          "RdYlGn_r",  False),
        ("throughput_tok_s", "Throughput (tok/s) ↑",   "RdYlGn",    True),
        ("vram_GB",          "VRAM (GB) ↓",            "RdYlGn_r",  False),
    ]

    valid = df[df["perplexity"].notna()].copy()
    if valid.empty:
        print("[WARN] Tidak ada hasil valid untuk divisualisasikan.")
        return

    fig, axes = plt.subplots(1, len(METRICS), figsize=(5 * len(METRICS), max(4, len(valid) * 0.9 + 2)))
    fig.suptitle(
        "Perbandingan Base LLMs\n"
        "Dataset: alvinrifky/Crawling-MKN_1 (2%) + WikiText-2 test (20% dari main sample)",
        fontsize=12, fontweight="bold", y=1.02,
    )

    for ax, (col, title, cmap_name, higher_is_better) in zip(axes, METRICS):
        if col not in valid.columns or valid[col].isna().all():
            ax.set_visible(False)
            continue

        sub  = valid[["model", col]].dropna().copy()
        sub["label"] = sub["model"].str.split("/").str[-1]
        sub  = sub.sort_values(col, ascending=not higher_is_better)
        vals = sub[col].tolist()
        lbls = sub["label"].tolist()

        cmap   = plt.colormaps[cmap_name]
        colors = [cmap(i / max(len(vals) - 1, 1)) for i in range(len(vals))]
        bars   = ax.barh(lbls, vals, color=colors, edgecolor="white", height=0.55)

        x_off = max(vals) * 0.01
        for bar, val in zip(bars, vals):
            ax.text(
                val + x_off,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,.2f}", va="center", fontsize=9, fontweight="bold",
            )

        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.1f}"))
        ax.invert_yaxis()
        ax.grid(axis="x", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n[INFO] Grafik disimpan → {output_file}")


# ─────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────
def main():
    import pandas as pd

    check_and_fix_environment()
    hf_token = setup_hf_token()

    # Load + mix + shuffle sekali, semua model pakai data yang sama
    texts = load_eval_texts()

    results = []
    for model_name in MODELS:
        res = compute_perplexity(model_name, texts, hf_token=hf_token)
        results.append(res)
        pd.DataFrame(results).to_csv(RESULTS_FILE, index=False)
        print(f"[INFO] Progress tersimpan → {RESULTS_FILE}")

    df = pd.DataFrame(results)

    print("\n" + "=" * 60)
    print("RINGKASAN HASIL")
    print("=" * 60)

    valid = df[df["perplexity"].notna()].sort_values("perplexity").copy()
    valid["model_short"] = valid["model"].str.split("/").str[-1]

    COLS = ["model_short", "params_B", "perplexity", "latency_sec", "throughput_tok_s", "vram_GB"]
    COLS = [c for c in COLS if c in valid.columns]

    if not valid.empty:
        print(valid[COLS].to_string(index=False))
        best = valid.iloc[0]
        print(f"\n🏆 Model terbaik (PPL) : {best['model_short']}  →  PPL = {best['perplexity']:,.4f}")
    else:
        print("Tidak ada model yang berhasil dievaluasi.")

    failed = df[df["error"].notna()]
    if not failed.empty:
        print("\n⚠️  Model yang gagal/dilewati:")
        for _, row in failed.iterrows():
            print(f"   • {row['model'].split('/')[-1]}: {row['error'][:120]}")

    df.to_csv(RESULTS_FILE, index=False)
    print(f"\n[INFO] Hasil final → {RESULTS_FILE}")
    plot_results(df)


if __name__ == "__main__":
    main()