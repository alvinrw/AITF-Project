#!/usr/bin/env python3
"""
API Inferensi — Qwen2.5-0.5B-AITF-SFT
=======================================
REST API sederhana untuk model analisis profil kesejahteraan sosial.

Jalankan:
    pip install fastapi uvicorn transformers accelerate bitsandbytes
    python api.py --model-path /home/jovyan/Testing/output/sft_qwen_05b_final-V2_merged

Endpoint:
    GET  /health           → Status server & model
    POST /predict          → Inferensi (input teks profil keluarga)
    POST /v1/chat          → Alternatif format chat messages

Contoh request:
    curl -X POST http://localhost:8000/predict \
         -H "Content-Type: application/json" \
         -d '{"text": "Profil Keluarga: ..."}'
"""

import os
import gc
import time
import argparse
import warnings
from pathlib import Path
from contextlib import asynccontextmanager

warnings.filterwarnings("ignore")

import secrets

import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# ── Argument Parsing ───────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="API Inferensi AITF SFT Model")
    parser.add_argument(
        "--model-path", type=str,
        default="/home/jovyan/Testing/output/sft_qwen_05b_final-V2_merged",
        help="Path ke folder merged model SFT"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host server")
    parser.add_argument("--port", type=int, default=8000, help="Port server")
    parser.add_argument("--max-new-tokens", type=int, default=512, help="Maks token output")
    parser.add_argument("--no-quantize", action="store_true", help="Matikan 4-bit quantization (untuk CPU)")
    parser.add_argument(
        "--api-key", type=str,
        default=os.environ.get("AITF_API_KEY", ""),
        help="API Key wajib disertakan di header X-API-Key. Bisa juga di-set via env AITF_API_KEY"
    )
    return parser.parse_args()

ARGS = parse_args()

# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Anda adalah sistem ahli analisis profil kesejahteraan sosial yang objektif dan presisi. 
Tugas Anda: 
1. Menganalisis kondisi sosial-ekonomi keluarga berdasarkan deskripsi yang diberikan. 
2. Memberikan penalaran (reasoning) komprehensif yang mencakup aspek: 
- Kepemilikan aset dan kualitas hunian. 
- Komposisi anggota keluarga dan beban ketergantungan. 
- Stabilitas pendapatan dan akses kebutuhan dasar.
3. Menentukan estimasi desil nasional (1-10) berdasarkan kriteria kemiskinan makro yang berlaku.
Gunakan format output berikut: 
- Analisis Kondisi: (Bedah poin-poin krusial dari deskripsi) 
- Reasoning: (Penjelasan mengapa keluarga tersebut masuk ke kategori desil tertentu, hubungkan antar variabel) 
- Skor Evaluasi: (Pilihan, masukkan angka prediksi)
- Desil Nasional: (Tuliskan HANYA satu angka 1 hingga 10 yang merupakan hasil akhir prediksi)"""

# ── Global State ───────────────────────────────────────────────────────────────

model = None
tokenizer = None
device = None
model_info = {}

# ── Model Loader ───────────────────────────────────────────────────────────────

def load_model():
    global model, tokenizer, device, model_info

    model_path = Path(ARGS.model_path)
    if not model_path.is_dir():
        raise RuntimeError(f"❌ Model tidak ditemukan: {model_path}")

    has_gpu = torch.cuda.is_available()
    device  = "cuda" if has_gpu else "cpu"
    use_quantize = has_gpu and not ARGS.no_quantize

    print(f"\n{'='*60}")
    print(f"  AITF SFT Inference API")
    print(f"{'='*60}")
    print(f"  Model Path : {model_path}")
    print(f"  Device     : {device.upper()}")
    print(f"  GPU        : {torch.cuda.get_device_name(0) if has_gpu else 'Tidak ada (CPU mode)'}")
    if has_gpu:
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  VRAM       : {vram:.1f} GB")
    print(f"  Quantize   : {'4-bit NF4' if use_quantize else 'None (FP32/FP16)'}")
    print(f"{'='*60}\n")

    # Load tokenizer
    print("📥 Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_path),
        trust_remote_code=True,
        padding_side="left",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    print("📥 Loading model...")
    t0 = time.time()

    if use_quantize:
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=dtype,
        )
    else:
        # CPU atau GPU tanpa quantization
        dtype = torch.float32 if not has_gpu else torch.float16
        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            device_map="auto" if has_gpu else None,
            trust_remote_code=True,
            torch_dtype=dtype,
        )
        if not has_gpu:
            model = model.to("cpu")

    model.eval()
    load_time = time.time() - t0

    model_info = {
        "model_path"   : str(model_path),
        "device"       : device,
        "gpu_name"     : torch.cuda.get_device_name(0) if has_gpu else "CPU",
        "quantized"    : use_quantize,
        "dtype"        : str(dtype),
        "load_time_s"  : round(load_time, 2),
        "max_new_tokens": ARGS.max_new_tokens,
    }

    print(f"✅ Model siap! (Load time: {load_time:.1f}s)\n")

# ── Inference ──────────────────────────────────────────────────────────────────

def run_inference(user_text: str, max_new_tokens: int = None) -> tuple[str, float]:
    """Jalankan inferensi. Return (output_text, elapsed_seconds)."""
    if model is None or tokenizer is None:
        raise RuntimeError("Model belum di-load")

    max_new_tokens = max_new_tokens or ARGS.max_new_tokens

    messages = [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": user_text},
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    input_len = inputs["input_ids"].shape[-1]

    t0 = time.time()
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens     = max_new_tokens,
            do_sample          = False,
            pad_token_id       = tokenizer.pad_token_id,
            eos_token_id       = tokenizer.eos_token_id,
        )
    elapsed = time.time() - t0

    new_ids = output_ids[0][input_len:]
    result  = tokenizer.decode(new_ids, skip_special_tokens=True).strip()

    # Post-processing: Potong teks sampah (generation loop) setelah Desil Nasional keluar
    import re
    if "Desil Nasional:" in result:
        parts = result.split("Desil Nasional:")
        before = parts[0]
        after = parts[1].strip()
        # Ambil hanya angkanya saja dari bagian after
        m = re.search(r'^(\d+)', after)
        if m:
            clean_after = m.group(1)
            result = f"{before}\nDesil Nasional: {clean_after}"
        else:
            # Fallback jika ternyata tidak ada angka
            result = f"{before}\nDesil Nasional: " + after.split("\n")[0]

    return result, round(elapsed, 3)

# ── FastAPI App ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()   # Load saat startup
    yield
    # Cleanup saat shutdown
    global model, tokenizer
    del model, tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("\n🛑 Server shutdown, model unloaded.")

app = FastAPI(
    title       = "AITF Welfare Analysis API",
    description = "API Analisis Profil Kesejahteraan Sosial — Qwen2.5-0.5B-AITF-SFT",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── API Key Auth ───────────────────────────────────────────────────────────────

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(key: str = Security(api_key_header)):
    """Validasi X-API-Key header. Lewati jika --api-key tidak di-set (mode dev)."""
    configured_key = ARGS.api_key
    if not configured_key:
        # Mode dev: tidak ada key yang dikonfigurasi → semua request diterima
        return
    if not key:
        raise HTTPException(status_code=401, detail="X-API-Key header wajib disertakan.")
    if not secrets.compare_digest(key, configured_key):
        raise HTTPException(status_code=403, detail="API Key tidak valid.")

# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    text: str = Field(..., description="Deskripsi profil keluarga yang akan dianalisis", min_length=10)
    max_new_tokens: int = Field(default=512, ge=50, le=2048, description="Maksimum token output")

class PredictResponse(BaseModel):
    result: str
    elapsed_seconds: float
    input_length: int

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_new_tokens: int = Field(default=512, ge=50, le=2048)

# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Cek status server dan model. Endpoint ini TIDAK butuh API Key."""
    return {
        "status"         : "ok" if model is not None else "loading",
        "model_loaded"   : model is not None,
        "auth_enabled"   : bool(ARGS.api_key),
        **model_info,
    }

@app.post("/predict", response_model=PredictResponse, tags=["Inference"])
def predict(req: PredictRequest, _: None = Security(verify_api_key)):
    """
    Analisis profil kesejahteraan keluarga.

    Input: teks deskripsi kondisi keluarga.
    Output: analisis + reasoning + Skor Evaluasi + Desil Nasional.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model sedang loading, coba lagi sebentar.")

    try:
        result, elapsed = run_inference(req.text, req.max_new_tokens)
        return PredictResponse(
            result          = result,
            elapsed_seconds = elapsed,
            input_length    = len(req.text),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/v1/chat", tags=["Inference"])
def chat(req: ChatRequest, _: None = Security(verify_api_key)):
    """
    Format alternatif — kirim messages langsung (seperti format OpenAI).
    Sistem akan mengabaikan system message dari request dan pakai prompt bawaan model.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model sedang loading, coba lagi sebentar.")

    # Ambil hanya pesan user terakhir
    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="Tidak ada pesan 'user' dalam messages.")

    user_text = user_msgs[-1].content
    try:
        result, elapsed = run_inference(user_text, req.max_new_tokens)
        return {
            "choices": [{"message": {"role": "assistant", "content": result}}],
            "elapsed_seconds": elapsed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host    = ARGS.host,
        port    = ARGS.port,
        workers = 1,     # Harus 1 — model tidak thread-safe untuk multi-worker
        reload  = False,
    )
