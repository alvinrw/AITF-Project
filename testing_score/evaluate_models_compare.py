import os
import gc
import json
import time
import argparse
import re
import math
import torch
import numpy as np
from typing import List, Dict
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM

# ============================================================
# ⚙️ CONFIGURATION
# ============================================================
DEVICE         = "cuda" if torch.cuda.is_available() else "cpu"
MAX_PPL_TOKENS = 512
DEFAULT_BATCH  = 4

MMLU_SUBJECTS = [
    "high_school_geography", "high_school_world_history",
    "international_law", "logical_fallacies", "philosophy",
    "sociology", "world_religions", "global_facts"
]
MMLU_SAMPLES_PER_SUBJECT = 20  
ARC_SAMPLES = 50

_HOME = os.path.expanduser('~')
CPT_05B_PATH = os.path.join(_HOME, 'Testing', 'output', 'qwen_cpt_v3_final')

MODELS_TO_TEST = {
    "Base Model":      "Qwen/Qwen2.5-0.5B",
    "Instruct Model":  "Qwen/Qwen2.5-0.5B-Instruct",
    "CPT Model":       CPT_05B_PATH
}

# ============================================================
# 📊 METRIK 1: PERPLEXITY (Domain Knowledge)
# ============================================================
def compute_perplexity(model, tokenizer, texts: List[str], batch_size: int) -> float:
    total_nll    = 0.0
    total_tokens = 0

    for i in tqdm(range(0, len(texts), batch_size), desc="  -> Computing PPL"):
        batch_texts = texts[i : i + batch_size]
        encoded = tokenizer(
            batch_texts, return_tensors="pt", padding=True,
            truncation=True, max_length=MAX_PPL_TOKENS,
        ).to(DEVICE)

        input_ids      = encoded["input_ids"]
        attention_mask = encoded["attention_mask"]

        labels = input_ids.clone()
        labels[attention_mask == 0] = -100

        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            
        # NLL / loss adalah Rata-rata dari semua token non-padding di batch
        # Jadi total_loss_batch = mean_loss * total_non_padding_tokens
        valid_tokens = (labels != -100).sum().item()
        
        if valid_tokens > 0:
            total_nll    += outputs.loss.item() * valid_tokens
            total_tokens += valid_tokens

    return math.exp(total_nll / total_tokens) if total_tokens > 0 else float('inf')

# ============================================================
# 🧠 METRIK 2 & 3: MMLU & ARC ACCURACY (General Knowledge)
# ============================================================
def _load_mmlu_subset() -> List[Dict]:
    from datasets import load_dataset
    all_items = []
    print(f"  📥 Loading MMLU ({len(MMLU_SUBJECTS)} subjects)...")
    for subject in MMLU_SUBJECTS:
        try:
            # trust_remote_code=True dihapus sesuai versi terbaru HF Datasets
            ds = load_dataset("cais/mmlu", subject, split="test")
            for item in list(ds)[:MMLU_SAMPLES_PER_SUBJECT]:
                all_items.append({
                    "question": item["question"], 
                    "choices": item["choices"], 
                    "answer_idx": item["answer"]
                })
        except Exception as e: print(f"MMLU Error {subject}: {e}")
    return all_items

def _load_arc_challenge() -> List[Dict]:
    from datasets import load_dataset
    all_items = []
    print(f"  📥 Loading ARC-Challenge...")
    try:
        # trust_remote_code=True dihapus
        ds = load_dataset("allenai/ai2_arc", "ARC-Challenge", split="test")
        for item in list(ds)[:ARC_SAMPLES]:
            choices_text  = item["choices"]["text"]
            choices_label = item["choices"]["label"]
            
            if len(choices_text) != 4:
                continue
                
            # Mapping ARC label ("1","2","3","4" atau "A","B","C","D") ke index 0-3
            key = item["answerKey"]
            try:
                if key in ["1", "2", "3", "4"]:
                    answer_idx = int(key) - 1
                else:
                    answer_idx = ["A", "B", "C", "D"].index(key.upper())
            except ValueError:
                continue
                
            all_items.append({
                "question": item["question"], 
                "choices": choices_text, 
                "answer_idx": answer_idx
            })
    except Exception as e: print(f"ARC Error: {e}")
    return all_items

def extract_answer(raw: str) -> str:
    """Ekstraksi yang jauh lebih presisi agar tidak tersandung kata awalan 'Because'/'According'."""
    raw = raw.strip().upper()
    if not raw: return "X"
    
    # Pola eksplisit di awal kalimat. Cocok untuk tebakan murni seperti: "A", "A.", "A)", "A :"
    match_start = re.match(r'^([ABCD])(?:[\.\)\s:]|$)', raw)
    if match_start: 
        return match_start.group(1)
    
    # Fallback jika model menjawab panjang, cari ke dalam teks secara ketat pembatas kata
    match_body = re.search(r'\b([ABCD])\b', raw)
    return match_body.group(1) if match_body else "X"

def evaluate_mcq_benchmark(model, tokenizer, items: List[Dict], batch_size: int, desc="Benchmark") -> float:
    if not items: return 0.0
    all_predictions, all_correct = [], []

    for i in tqdm(range(0, len(items), batch_size), desc=f"  -> {desc}"):
        batch = items[i : i + batch_size]
        prompts = []
        for item in batch:
            choices_str = "\n".join(f"{l}. {t}" for l, t in zip(["A","B","C","D"], item["choices"]))
            prompts.append(f"{item['question']}\n\n{choices_str}\n\nJawaban yang benar adalah (A/B/C/D): ")

        inputs = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=512).to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs, max_new_tokens=4, do_sample=False,
                pad_token_id=tokenizer.eos_token_id, eos_token_id=tokenizer.eos_token_id
            )

        for j, output in enumerate(outputs):
            input_len  = inputs["input_ids"].shape[1]
            raw_answer = tokenizer.decode(output[input_len:], skip_special_tokens=True)
            predicted  = extract_answer(raw_answer)
            all_predictions.append(predicted)
            all_correct.append(["A", "B", "C", "D"][batch[j]["answer_idx"]])
            
            # Tambahan untuk Debugging Base Model MMLU Parsing
            if i == 0 and j < 3:
                print(f"\n[DEBUG] Raw output: {repr(raw_answer)}")
                print(f"[DEBUG] Extracted : {predicted}")
                print(f"[DEBUG] Correct   : {['A','B','C','D'][batch[j]['answer_idx']]}")

    correct_count = sum(p == c for p, c in zip(all_predictions, all_correct))
    return correct_count / len(all_correct)

# ============================================================
# 💾 LOAD / UNLOAD MODEL HELPER
# ============================================================
def load_model(path: str):
    # Menggunakan use_fast=False untuk menghindari warning tokenisasi regex di CPT Model
    tokenizer = AutoTokenizer.from_pretrained(path, use_fast=False)
    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    
    dtype = torch.bfloat16 if DEVICE == "cuda" else torch.float32
    print(f"  Memuat weights & model...")
    
    # Otomatis gunakan 4-bit jika memori kecil / BitsAndBytes tersedia
    try:
        from transformers import BitsAndBytesConfig
        bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=dtype)
        model = AutoModelForCausalLM.from_pretrained(path, quantization_config=bnb, device_map="auto")
        print("    ✅ Loaded with 4-bit Quantization")
    except ImportError:
        model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=dtype, device_map="auto")
        print("    ⚠️ BitsAndBytes not found, loaded without quantization")
        
    model.eval()
    return model, tokenizer

# ============================================================
# 🚀 MAIN PIPELINE
# ============================================================
def main():
    parser = argparse.ArgumentParser("Evaluasi CPT: Base vs CPT")
    parser.add_argument("--dataset_domain", type=str, required=True, help="Path ke JSON domain dataset")
    parser.add_argument("--dataset_general", type=str, required=True, help="Path ke JSON general dataset (opsional)")
    parser.add_argument("--batch_size", type=int, default=DEFAULT_BATCH)
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  🚀 MEMULAI EVALUASI PERBANDINGAN: BASE vs CPT")
    print("="*60)

    # 1. Load Datasets
    with open(args.dataset_domain, "r", encoding="utf-8") as f:
        domain_texts = [f"{i['question']} {i['answer']}" for i in json.load(f)]
    with open(args.dataset_general, "r", encoding="utf-8") as f:
        general_texts = [f"{i['question']} {i['answer']}" for i in json.load(f)]
        
    print(f"✅ Domain dataset loaded: {len(domain_texts)} baris")
    print(f"✅ General dataset loaded: {len(general_texts)} baris")

    mmlu_items = _load_mmlu_subset()
    arc_items  = _load_arc_challenge()
    print(f"✅ MMLU loaded: {len(mmlu_items)} soal | ARC loaded: {len(arc_items)} soal")

    results = {}

    for name, path in MODELS_TO_TEST.items():
        print(f"\n⚙️  Processing {name} ({path})")
        if not os.path.exists(path) and "Qwen" not in path:
            print(f"   ⚠️ Path CPT lokal {path} tidak ditemukan! Lewati.")
            continue
            
        model, tokenizer = load_model(path)
        
        ppl_dom = compute_perplexity(model, tokenizer, domain_texts, args.batch_size)
        ppl_gen = compute_perplexity(model, tokenizer, general_texts, args.batch_size)
        
        mmlu_acc = evaluate_mcq_benchmark(model, tokenizer, mmlu_items, args.batch_size, "Computing MMLU")
        arc_acc  = evaluate_mcq_benchmark(model, tokenizer, arc_items, args.batch_size, "Computing ARC")
        
        results[name] = {
            "ppl_domain": ppl_dom, "ppl_general": ppl_gen,
            "mmlu": mmlu_acc * 100, "arc": arc_acc * 100
        }

        # Clear GPU mem & garbage collection
        del model
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()

    if "Base Model" not in results:
        print("\n❌ Gagal membandingkan. Harus ada 'Base Model' sebagai patokan evaluasi.")
        return

    print("\n" + "="*100)
    print(f"{'Model':<16} | {'PPL Domain':<12} | {'PPL General':<12} | {'MMLU Acc':<12} | {'ARC Acc':<12}")
    print("-" * 100)
    for model_name, res in results.items():
        print(f"{model_name:<16} | {res['ppl_domain']:<12.2f} | {res['ppl_general']:<12.2f} | {res['mmlu']:<11.2f}% | {res['arc']:<11.2f}%")
    print("="*100)

    # 💾 SIMPAN KE JSON
    out_file = "evaluation_summary.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 Hasil eksekusi telah tersimpan permanen di {out_file}")

    print("\n🧠 ANALISIS CATASTROPHIC FORGETTING (Dibandingkan dengan Base Model):")
    base = results["Base Model"]
    
    for model_name, res in results.items():
        if model_name == "Base Model": 
            continue
            
        ppl_domain_gain  = base["ppl_domain"] - res["ppl_domain"]
        ppl_general_loss = res["ppl_general"] - base["ppl_general"]
        mmlu_drop        = base["mmlu"] - res["mmlu"]
        arc_drop         = base["arc"] - res["arc"]

        print(f"\n[{model_name.upper()}]")
        
        # 1. Domain
        if ppl_domain_gain > 0: 
            print(f"  ✅ Domain Mastery: BAIK. Model lebih meresapi domain Anda (PPL Turun {abs(ppl_domain_gain):.2f} poin)")
        else: 
            print(f"  ❌ Domain Mastery: BURUK. Model tersesat/gagal adaptasi (PPL Naik {abs(ppl_domain_gain):.2f} poin)")

        # 2. General Knowledge
        if mmlu_drop > 2.0 or arc_drop > 2.0:
            print(f"  🔴 MMLU/ARC (Catastrophic Forgetting) : TINGGI! Akurasi Benchmark turun (MMLU: -{mmlu_drop:.2f}%, ARC: -{arc_drop:.2f}%).")
        elif mmlu_drop > 0 or arc_drop > 0:
            print(f"  🟡 MMLU/ARC (Catastrophic Forgetting) : RINGAN. Akurasi sedikit goyah. Masih batas aman.")
        else:
            print(f"  ✅ MMLU/ARC (Catastrophic Forgetting) : SANGAT AMAN! Tidak ada degradasi logika malah membaik.")

if __name__ == "__main__":
    main()