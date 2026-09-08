from __future__ import annotations

import ctypes
import io
import logging
import os
from contextlib import asynccontextmanager

# Precarga explícita de librerías NVIDIA para CTranslate2 / CUDA 12
for _mod, _lib in [("nvidia.cublas.lib", "libcublas.so.12"), ("nvidia.cudnn.lib", "libcudnn.so.9")]:
    try:
        import importlib
        m = importlib.import_module(_mod)
        p = os.path.join(m.__path__[0], _lib)
        if os.path.exists(p):
            ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
    except Exception:
        pass

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
import torch

logger = logging.getLogger("whisper-service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

MODEL_NAME = os.getenv("WHISPER_MODEL", "medium")
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float16" if DEVICE == "cuda" else "int8")
BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "1"))
VAD_FILTER = os.getenv("WHISPER_VAD_FILTER", "false").lower() == "true"

_model: WhisperModel | None = None


def _load_model() -> None:
    global _model
    download_root = os.getenv("HF_HOME", "/models_cache")
    logger.info(
        "Iniciando Faster-Whisper: modelo=%s | device=%s | compute_type=%s | cache=%s",
        MODEL_NAME,
        DEVICE,
        COMPUTE_TYPE,
        download_root,
    )
    _model = WhisperModel(
        MODEL_NAME,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        download_root=download_root,
    )
    logger.info("Modelo Faster-Whisper cargado exitosamente y listo para peticiones.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield


app = FastAPI(title="Whisper STT Server", lifespan=lifespan)


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(None),
    response_format: str | None = Form("json"),
    language: str | None = Form(None),
    temperature: str | None = Form(None),
    prompt: str | None = Form(None),
):
    del model  # El modelo cargado está fijado en el servidor

    if _model is None:
        raise HTTPException(status_code=503, detail="Modelo Faster-Whisper aún no está listo")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Archivo de audio vacío")

    target_lang = language if (language and language.lower() not in ("auto", "none")) else "es"

    try:
        segments, info = _model.transcribe(
            io.BytesIO(audio_bytes),
            language=target_lang,
            beam_size=BEAM_SIZE,
            condition_on_previous_text=False,
            temperature=float(temperature) if temperature else 0.0,
            initial_prompt=prompt or None,
            vad_filter=VAD_FILTER,
            vad_parameters=dict(min_silence_duration_ms=250) if VAD_FILTER else None,
        )
        text = "".join(segment.text for segment in segments).strip()
        logger.info(
            "Transcripción completada: lang=%s | dur=%.2fs | text='%s'",
            info.language,
            info.duration,
            text,
        )
    except Exception as error:
        logger.exception("Fallo durante la transcripción de audio")
        raise HTTPException(status_code=500, detail=f"Error en transcripción: {error}") from error

    return JSONResponse(content={"text": text})


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "model_loaded": _model is not None,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "model": MODEL_NAME,
    }


@app.get("/v1/models")
async def list_models() -> JSONResponse:
    return JSONResponse(
        {
            "object": "list",
            "data": [
                {
                    "id": MODEL_NAME,
                    "object": "model",
                    "owned_by": "systran",
                }
            ],
        }
    )
