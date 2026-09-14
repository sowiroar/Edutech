"""
OpenAI-compatible STT server wrapping NVIDIA's
nemotron-3.5-asr-streaming-0.6b model.

Wraps NVIDIA's nemotron-3.5-asr-streaming-0.6b, a cache-aware
FastConformer-RNNT model. It's a *prompted* ASR model: a language-ID prompt
(`target_lang`) steers decoding, or `auto` lets the model detect the
language from the audio.

Exposes:
    POST /v1/audio/transcriptions   OpenAI-compatible (whole-file). The
                                    `language` form field selects a target
                                    language (e.g. "es-US"); omit it for `auto`.
    WS   /v1/audio/stream           Live PCM-in / text-deltas-out streaming.
                                    Send {"type": "config", "language": "es-US"}
                                    before audio to pin a language.
    GET  /v1/models                 Model listing.
    GET  /health                    Liveness/readiness.

Usage:
    export PYTORCH_ENABLE_MPS_FALLBACK=1
    python server.py [--host 0.0.0.0] [--port 8000]
"""

import argparse
import asyncio
import json
import logging
import os
import re
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

logger = logging.getLogger("stt-server")
logging.basicConfig(level=logging.INFO)

MODEL_NAME = "nvidia/nemotron-3.5-asr-streaming-0.6b"
MODEL_ID = "nemotron-3.5-asr-streaming-0.6b"
TARGET_SAMPLE_RATE = 16000
MEL_HOP_SAMPLES = 160

DEFAULT_TARGET_LANG = os.environ.get("STT_TARGET_LANG", "auto")

ATT_CONTEXT_SIZE = os.environ.get("STT_ATT_CONTEXT_SIZE", "[56,3]")

RECYCLE_MIN_CHARS = int(os.environ.get("STT_RECYCLE_MIN_CHARS", "50"))
RECYCLE_HARD_CHARS = int(os.environ.get("STT_RECYCLE_HARD_CHARS", "120"))
BACKLOG_RECYCLE_FRAMES = int(os.environ.get("STT_BACKLOG_RECYCLE_FRAMES", "25"))

asr_model = None


def _try_empty_cache(device) -> None:
    try:
        if torch.cuda.is_available() and "cuda" in str(device):
            torch.cuda.empty_cache()
        elif hasattr(torch, "mps") and "mps" in str(device):
            torch.mps.empty_cache()
    except Exception:
        pass


def _parse_att_context(s: str) -> list[int]:
    try:
        return [int(x) for x in s.strip("[] ").split(",") if x.strip()]
    except Exception:
        return [56, 3]


_LANG_TAG_RE = re.compile(r"\s*<[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?>\s*")


def _strip_lang_tags(text: str) -> str:
    return _LANG_TAG_RE.sub(" ", text).strip()


def _scfg_val(v):
    """Steady-state value from a streaming_cfg field.

    These fields are either a scalar or a 2-list ``[first_chunk, steady_state]``.
    We want the steady-state (index 1) value for continuous streaming.
    """
    if isinstance(v, (list, tuple)):
        return v[1] if len(v) > 1 else v[0]
    return v


def apply_target_lang(model, target_lang: str) -> str:
    """Condition the prompted RNNT decoder on a target language.

    Pass a code like "es-US", or "auto" for language-agnostic decoding. The
    prompt is set once before streaming; the per-chunk step injects it
    internally. Best-effort and never raises — an unknown language falls back
    to "auto".
    """
    lang = (target_lang or "auto").strip()
    try:
        if hasattr(model, "set_inference_prompt"):
            model.set_inference_prompt(lang)
        else:
            decoding_cfg = model.cfg.decoding
            decoding_cfg.target_lang = lang
            if hasattr(model, "change_decoding_strategy"):
                model.change_decoding_strategy(decoding_cfg)
    except Exception as e:
        logger.warning(
            "Could not set target_lang=%s (%s); falling back to model default", lang, e
        )
        if lang != "auto":
            return apply_target_lang(model, "auto")
    return lang


def load_model():
    global asr_model
    logger.info("Loading model %s ...", MODEL_NAME)
    import nemo.collections.asr as nemo_asr

    asr_model = nemo_asr.models.ASRModel.from_pretrained(MODEL_NAME)
    asr_model.eval()

    try:
        asr_model.encoder.set_default_att_context_size(_parse_att_context(ATT_CONTEXT_SIZE))
        logger.info("att_context_size = %s", ATT_CONTEXT_SIZE)
    except Exception as e:
        logger.warning("Could not set att_context_size=%s (%s)", ATT_CONTEXT_SIZE, e)
    apply_target_lang(asr_model, DEFAULT_TARGET_LANG)
    logger.info("default target_lang = %s", DEFAULT_TARGET_LANG)

    if torch.cuda.is_available():
        asr_model = asr_model.cuda()
        logger.info("Model on CUDA")
    elif torch.backends.mps.is_available():
        try:
            asr_model = asr_model.to("mps")
            logger.info("Model on MPS")
        except Exception:
            logger.info("MPS failed, using CPU")
    else:
        logger.info("Model on CPU")

    logger.info("Model loaded successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(title="NeMo STT Server", lifespan=lifespan)


def load_audio(audio_bytes: bytes, filename: str) -> np.ndarray:
    """Load audio bytes, resample to 16kHz mono, return float32 numpy array."""
    suffix = os.path.splitext(filename)[1] if filename else ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        tmp_in_path = tmp_in.name

    try:
        data, sr = sf.read(tmp_in_path, dtype="float32")
    except Exception:
        import torchaudio
        waveform, sr = torchaudio.load(tmp_in_path)
        data = waveform.numpy()
        if data.ndim == 2:
            data = data.mean(axis=0)
    finally:
        os.unlink(tmp_in_path)

    if data.ndim > 1:
        data = data.mean(axis=-1) if data.shape[-1] <= data.shape[0] else data.mean(axis=0)

    if sr != TARGET_SAMPLE_RATE:
        import torchaudio
        waveform = torch.tensor(data).unsqueeze(0)
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=TARGET_SAMPLE_RATE)
        waveform = resampler(waveform)
        data = waveform.squeeze(0).numpy()

    return data


def direct_transcribe(audio: np.ndarray) -> str:
    audio_tensor = torch.tensor(audio).unsqueeze(0).to(asr_model.device)
    audio_len = torch.tensor([audio.shape[0]], dtype=torch.long).to(asr_model.device)

    with torch.no_grad():
        processed, processed_len = asr_model.preprocessor(
            input_signal=audio_tensor, length=audio_len,
        )
        encoded, encoded_len = asr_model.encoder(
            audio_signal=processed, length=processed_len,
        )
        hypotheses = asr_model.decoding.rnnt_decoder_predictions_tensor(
            encoded, encoded_len, return_hypotheses=False,
        )
        return hypotheses[0].text


def streaming_transcribe(audio: np.ndarray):
    """Yield incremental transcript deltas using conformer_stream_step."""
    model = asr_model
    device = model.device

    audio_tensor = torch.tensor(audio).unsqueeze(0).to(device)
    audio_len = torch.tensor([audio.shape[0]], dtype=torch.long).to(device)

    with torch.no_grad():
        processed, processed_len = model.preprocessor(
            input_signal=audio_tensor, length=audio_len,
        )

        scfg = model.encoder.streaming_cfg
        cs = scfg.chunk_size[0] if isinstance(scfg.chunk_size, (list, tuple)) else scfg.chunk_size
        ss = scfg.shift_size[0] if isinstance(scfg.shift_size, (list, tuple)) else scfg.shift_size
        pre_cache = scfg.pre_encode_cache_size
        pre_cache = pre_cache[0] if isinstance(pre_cache, (list, tuple)) else pre_cache

        total_frames = processed.shape[2]
        prev_text = ""
        previous_hypotheses = None

        cache_last_channel, cache_last_time, cache_last_channel_len = (
            model.encoder.get_initial_cache_state(batch_size=1)
        )

        if pre_cache > 0:
            pad = torch.zeros(
                processed.shape[0], processed.shape[1], pre_cache,
                device=device, dtype=processed.dtype,
            )
            processed = torch.cat([pad, processed], dim=2)
            total_frames = processed.shape[2]

        offset = 0
        while offset < total_frames:
            end = min(offset + cs, total_frames)
            chunk = processed[:, :, offset:end]
            chunk_len = torch.tensor([chunk.shape[2]], dtype=torch.long).to(device)

            result = model.conformer_stream_step(
                processed_signal=chunk,
                processed_signal_length=chunk_len,
                cache_last_channel=cache_last_channel,
                cache_last_time=cache_last_time,
                cache_last_channel_len=cache_last_channel_len,
                previous_hypotheses=previous_hypotheses,
                return_transcription=True,
            )

            (
                _preds,
                all_hyps,
                cache_last_channel,
                cache_last_time,
                cache_last_channel_len,
                best_hyp,
            ) = result

            if best_hyp and len(best_hyp) > 0:
                hyp = best_hyp[0]
                current_text = hyp.text if hasattr(hyp, "text") else str(hyp)
            elif isinstance(all_hyps, list) and len(all_hyps) > 0:
                if isinstance(all_hyps[0], str):
                    current_text = all_hyps[0]
                elif hasattr(all_hyps[0], "text"):
                    current_text = all_hyps[0].text
                else:
                    current_text = str(all_hyps[0])
            else:
                current_text = ""

            previous_hypotheses = best_hyp

            if current_text and current_text != prev_text:
                delta = current_text[len(prev_text):]
                if delta:
                    yield delta
                prev_text = current_text

            offset += ss


async def sse_generator(audio: np.ndarray):
    full_text = ""
    for delta in streaming_transcribe(audio):
        full_text += delta
        event = {"type": "transcript.text.delta", "delta": delta}
        yield f"data: {json.dumps(event)}\n\n"

    done_event = {"type": "transcript.text.done", "text": full_text.strip()}
    yield f"data: {json.dumps(done_event)}\n\n"
    yield "data: [DONE]\n\n"


class _CacheFeatureBuffer:
    """Rolling ``(pre_encode_cache + chunk)`` mel-feature window for cache-aware
    streaming.

    Each step exposes a window whose leading ``precache`` frames are the real
    previous-chunk features (the encoder's left context) and whose trailing
    ``chunk`` frames are new — exactly what cache-aware streaming consumes. Two
    details make small / low-latency chunks decode correctly:

    * Features are extracted **without** normalization and the **whole window is
      normalized together** on read, so normalization statistics stay
      consistent across chunks. Per-chunk normalization swings wildly between
      chunks and collapses the transcript at small chunk sizes.
    * A short audio look-back is prepended before feature extraction so the
      chunk's first mel frame is windowed continuously across the seam.

    This is the incremental, single-stream form of NeMo's
    ``CacheAwareStreamingAudioBuffer`` / ``StreamingFeatureBufferer``
    (``nemo.collections.asr.parts.utils.streaming_utils``).
    """

    def __init__(self, model, chunk_frames: int, precache_frames: int):
        import copy

        from omegaconf import OmegaConf
        from nemo.collections.asr.parts.preprocessing.features import normalize_batch

        self._normalize_batch = normalize_batch
        self.device = model.device
        self.chunk_frames = chunk_frames
        self.precache_frames = precache_frames
        self.buffer_frames = precache_frames + chunk_frames
        self.hop = MEL_HOP_SAMPLES
        self.chunk_samples = chunk_frames * self.hop
        self.look_back = 2 * self.hop

        cfg = copy.deepcopy(model._cfg)
        OmegaConf.set_struct(cfg.preprocessor, False)
        self.normalize_type = cfg.preprocessor.normalize
        cfg.preprocessor.normalize = "None"
        cfg.preprocessor.dither = 0.0
        cfg.preprocessor.pad_to = 0
        self.raw_preprocessor = model.from_config_dict(cfg.preprocessor).to(self.device)
        self.n_feat = cfg.preprocessor.features
        self.reset()

    def reset(self) -> None:
        self.sample_ring = torch.zeros(
            self.chunk_samples + self.look_back, dtype=torch.float32, device=self.device
        )
        silence = torch.zeros(
            self.buffer_frames * self.hop + self.look_back,
            dtype=torch.float32, device=self.device,
        )
        zero_level = self._extract(silence)[:, :1]
        self.feature_buffer = zero_level.repeat(1, self.buffer_frames).contiguous()

    def _extract(self, samples: torch.Tensor) -> torch.Tensor:
        signal = samples.unsqueeze(0)
        length = torch.tensor([samples.shape[0]], device=self.device)
        feats, _ = self.raw_preprocessor(input_signal=signal, length=length)
        return feats.squeeze(0)

    def update(self, chunk_audio: torch.Tensor) -> None:
        """Shift one ``chunk_frames`` chunk of audio into the rolling window."""
        ring = self.sample_ring
        ring[: -self.chunk_samples] = ring[self.chunk_samples :].clone()
        ring[-self.chunk_samples :] = chunk_audio
        feats = self._extract(ring)
        chunk_feats = feats[:, -self.chunk_frames :]
        if chunk_feats.shape[1] < self.chunk_frames:
            pad = self.feature_buffer[:, -1:].repeat(1, self.chunk_frames - chunk_feats.shape[1])
            chunk_feats = torch.cat([pad, chunk_feats], dim=1)
        self.feature_buffer[:, : -self.chunk_frames] = self.feature_buffer[:, self.chunk_frames :].clone()
        self.feature_buffer[:, -self.chunk_frames :] = chunk_feats

    def normalized_window(self):
        """Return ``(processed_signal, length)`` for the whole window."""
        x = self.feature_buffer.unsqueeze(0)
        seq_len = torch.tensor([self.buffer_frames], device=self.device)
        normed, _, _ = self._normalize_batch(
            x=x, seq_len=seq_len, normalize_type=self.normalize_type
        )
        return normed, seq_len


class StreamingASR:
    """Stateful wrapper around conformer_stream_step for an open audio stream.

    Audio is fed as float32 PCM @ 16kHz mono. Internally we buffer raw samples,
    preprocess into mel frames a chunk at a time, and run cache-aware streaming
    steps. The hypothesis text returned by the RNNT decoder is cumulative — we
    report the running cumulative text on every chunk.

    State is held for the lifetime of the WebSocket connection. We do NOT reset
    state on silence: the conformer's cache is fixed-size, and the RNNT
    hypothesis only grows while there are actual non-silent tokens (so long
    pauses are cheap). Resetting mid-utterance during normal breath pauses
    corrupts the transcript ("things. that you can deploy" lowercase, missing
    spaces, etc.) and is what broke teleprompter tracking in earlier versions.
    Explicit `{"type": "reset"}` or `{"type": "flush"}` from the client still
    works for callers that need it.
    """

    def __init__(self, model, target_lang: str = DEFAULT_TARGET_LANG):
        self.model = model
        self.device = model.device
        self.target_lang = apply_target_lang(model, target_lang)

        scfg = model.encoder.streaming_cfg
        self.chunk_mel_frames = _scfg_val(scfg.chunk_size)
        self.chunk_audio_samples = self.chunk_mel_frames * MEL_HOP_SAMPLES
        self.precache_mel = _scfg_val(scfg.pre_encode_cache_size)
        self.drop_extra_pre_encoded = getattr(scfg, "drop_extra_pre_encoded", 0)

        self._buffer = _CacheFeatureBuffer(model, self.chunk_mel_frames, self.precache_mel)
        self.reset()

    def reset(self):
        self.cache_ch, self.cache_t, self.cache_ch_len = (
            self.model.encoder.get_initial_cache_state(batch_size=1)
        )
        self.previous_hypotheses = None
        self.current_text = ""
        self.audio_buffer = np.zeros(0, dtype=np.float32)
        self._buffer.reset()
        self._chunks_since_cache_clear = 0

    def set_target_lang(self, target_lang: str) -> None:
        """Re-prompt the decoder mid-connection and reset stream state.

        Switching languages changes the decoder prompt, so we reset the encoder
        cache and RNNT hypothesis to avoid bleeding context across languages.
        """
        self.target_lang = apply_target_lang(self.model, target_lang)
        self.reset()

    def feed(self, pcm_f32: np.ndarray) -> bool:
        """Append samples and process whole chunks. Returns True if text grew."""
        if pcm_f32.size > 0:
            self.audio_buffer = np.concatenate([self.audio_buffer, pcm_f32])

        changed = False
        while len(self.audio_buffer) >= self.chunk_audio_samples:
            chunk = self.audio_buffer[: self.chunk_audio_samples]
            self.audio_buffer = self.audio_buffer[self.chunk_audio_samples :]
            new_text = self._process_chunk(chunk)
            if new_text != self.current_text:
                self.current_text = new_text
                changed = True

            self._chunks_since_cache_clear += 1
            if self._chunks_since_cache_clear >= 50:
                self._chunks_since_cache_clear = 0
                _try_empty_cache(self.device)
        return changed

    def flush(self) -> str:
        """Drain any leftover audio, return the final cumulative text, then reset."""
        leftover = self.audio_buffer
        if 0 < len(leftover) < self.chunk_audio_samples:
            leftover = np.concatenate(
                [leftover, np.zeros(self.chunk_audio_samples - len(leftover), dtype=np.float32)]
            )
        if len(leftover) >= self.chunk_audio_samples:
            new_text = self._process_chunk(leftover[: self.chunk_audio_samples], is_final=True)
            if new_text:
                self.current_text = new_text
        self.audio_buffer = np.zeros(0, dtype=np.float32)
        final = self.current_text.strip()
        self.reset()
        return final

    def should_recycle(self) -> bool:
        """True when the cumulative hypothesis should be committed and the
        stream restarted.

        Cache-aware streaming carries an ever-growing RNNT hypothesis; with no
        VAD to flush between utterances (a teleprompter reads without pausing),
        it eventually stalls. We bound it: cut at a sentence boundary once the
        text is long enough, and force a cut past a hard limit.
        """
        t = self.current_text.rstrip()
        if len(t) >= RECYCLE_HARD_CHARS:
            return True
        return len(t) >= RECYCLE_MIN_CHARS and t.endswith((".", "!", "?", "。", "！", "？"))

    def recycle(self) -> str:
        """Commit the current text and reset streaming state."""
        committed = self.current_text.strip()
        self.reset()
        return committed

    def _process_chunk(self, audio: np.ndarray, is_final: bool = False) -> str:
        with torch.no_grad():
            chunk = torch.from_numpy(np.ascontiguousarray(audio)).float().to(self.device)
            self._buffer.update(chunk)
            processed, processed_len = self._buffer.normalized_window()

            result = self.model.conformer_stream_step(
                processed_signal=processed,
                processed_signal_length=processed_len,
                cache_last_channel=self.cache_ch,
                cache_last_time=self.cache_t,
                cache_last_channel_len=self.cache_ch_len,
                keep_all_outputs=is_final,
                previous_hypotheses=self.previous_hypotheses,
                drop_extra_pre_encoded=self.drop_extra_pre_encoded,
                return_transcription=True,
            )

            (_preds, _all_hyps, ch, ct, ch_len, best_hyp) = result
            self.cache_ch = ch
            self.cache_t = ct
            self.cache_ch_len = ch_len
            self.previous_hypotheses = best_hyp

            if best_hyp and len(best_hyp) > 0:
                hyp = best_hyp[0]
                text = hyp.text if hasattr(hyp, "text") else str(hyp)
                return _strip_lang_tags(text)
            return self.current_text


_AUDIO_QUEUE_WARN_LEN = 200


@app.websocket("/v1/audio/stream")
async def stream_endpoint(ws: WebSocket):
    """Bidirectional live STT.

    Client → Server:
        binary frames: int16 little-endian PCM @ 16kHz mono.
        text frames: JSON control messages.
            {"type": "config", "language": "es-US"}
                                – set the target language (or "auto"); resets
                                  state. Send before audio to pin a language.
            {"type": "flush"}   – emit a final, reset state, keep socket open.
            {"type": "reset"}   – silently reset state.

    Server → Client (text frames):
        {"type": "ready"}                                  – on accept.
        {"type": "delta", "text": "<cumulative text>"}     – text grew.
        {"type": "final", "text": "<final text>"}          – after explicit
            flush from the client.
        {"type": "error", "message": "..."}                – fatal error.

    Internally we split message receiving from inference: the reader pulls
    frames into a bounded queue; the worker drains the queue and runs the
    model. That keeps the WebSocket reader loop responsive (so server-side
    pings keep flowing) even when inference falls behind realtime.
    """
    await ws.accept()
    if asr_model is None:
        await ws.send_text(json.dumps({"type": "error", "message": "model not loaded"}))
        await ws.close(code=1011)
        return

    streamer = StreamingASR(asr_model)
    queue: asyncio.Queue = asyncio.Queue()
    closed = asyncio.Event()
    last_backlog_warn = 0.0
    await ws.send_text(json.dumps({"type": "ready"}))

    async def reader() -> None:
        nonlocal last_backlog_warn
        try:
            while not closed.is_set():
                msg = await ws.receive()
                mtype = msg.get("type", "")
                if mtype == "websocket.disconnect":
                    closed.set()
                    return

                data_bytes = msg.get("bytes")
                if data_bytes:
                    queue.put_nowait(("audio", data_bytes))
                    qsize = queue.qsize()
                    if qsize >= _AUDIO_QUEUE_WARN_LEN:
                        now = time.time()
                        if now - last_backlog_warn > 2.0:
                            logger.warning(
                                "audio backlog: %d queued frames (~%.1fs of audio)"
                                " — inference is falling behind realtime",
                                qsize,
                                qsize * 0.05,
                            )
                            last_backlog_warn = now
                    continue

                data_text = msg.get("text")
                if data_text:
                    queue.put_nowait(("ctrl", data_text))
        except WebSocketDisconnect:
            closed.set()
        except Exception:
            logger.exception("reader task error")
            closed.set()
        finally:
            await queue.put(("eof", None))

    async def worker() -> None:
        try:
            while not closed.is_set():
                kind, payload = await queue.get()
                try:
                    if kind == "eof":
                        return
                    if kind == "audio":
                        pcm_int16 = np.frombuffer(payload, dtype=np.int16)
                        pcm_f32 = pcm_int16.astype(np.float32) / 32768.0
                        changed = await asyncio.to_thread(streamer.feed, pcm_f32)
                        backlogged = queue.qsize() >= BACKLOG_RECYCLE_FRAMES
                        if (streamer.should_recycle() or backlogged) and streamer.current_text.strip():
                            committed = await asyncio.to_thread(streamer.recycle)
                            if committed:
                                await ws.send_text(json.dumps({
                                    "type": "final",
                                    "text": committed,
                                }))
                        elif changed:
                            await ws.send_text(json.dumps({
                                "type": "delta",
                                "text": streamer.current_text,
                            }))
                    elif kind == "ctrl":
                        try:
                            ctrl = json.loads(payload)
                        except Exception:
                            continue
                        t = ctrl.get("type")
                        if t == "config":
                            lang = ctrl.get("language") or DEFAULT_TARGET_LANG
                            await asyncio.to_thread(streamer.set_target_lang, lang)
                            await ws.send_text(json.dumps({
                                "type": "config",
                                "language": streamer.target_lang,
                            }))
                        elif t == "flush":
                            final = await asyncio.to_thread(streamer.flush)
                            await ws.send_text(json.dumps({
                                "type": "final",
                                "text": final,
                            }))
                        elif t == "reset":
                            streamer.reset()
                finally:
                    queue.task_done()
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.exception("worker task error")
            try:
                await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
            except Exception:
                pass

    reader_task = asyncio.create_task(reader())
    worker_task = asyncio.create_task(worker())
    try:
        done, pending = await asyncio.wait(
            [reader_task, worker_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        closed.set()
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
    finally:
        if not closed.is_set():
            closed.set()


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(MODEL_ID),
    response_format: Optional[str] = Form("json"),
    stream: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    temperature: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
):
    if asr_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    is_stream = stream is not None and stream.lower() in ("true", "1", "yes")

    resolved_lang = apply_target_lang(asr_model, language or DEFAULT_TARGET_LANG)

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        audio = load_audio(audio_bytes, file.filename or "audio.wav")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process audio: {e}")

    if is_stream:
        return StreamingResponse(
            sse_generator(audio),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        text = direct_transcribe(audio)
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    if response_format == "text":
        return JSONResponse(content=text, media_type="text/plain")
    elif response_format == "verbose_json":
        return JSONResponse(content={
            "text": text,
            "task": "transcribe",
            "language": resolved_lang,
            "duration": None,
        })
    else:
        return JSONResponse(content={"text": text})


@app.get("/v1/models")
async def list_models():
    return JSONResponse(content={
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "nvidia",
            }
        ],
    })


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": asr_model is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeMo STT Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
