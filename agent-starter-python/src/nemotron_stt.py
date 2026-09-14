from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import AsyncIterator

import numpy as np
import onnxruntime_genai as og
from huggingface_hub import snapshot_download

from livekit import rtc
from livekit.agents import stt
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
from livekit.agents.utils import AudioBuffer

logger = logging.getLogger("nemotron-stt")

# Mapeo de códigos de idioma canónicos de Nemotron-3.5-ASR-Streaming-Multilingual
LANG_TO_ID = {
    "en": 0,
    "en-US": 0,
    "en-GB": 1,
    "es-ES": 2,
    "es": 3,
    "es-US": 3,
    "es-419": 3,
    "zh-CN": 4,
    "hi": 6,
    "hi-IN": 6,
    "ar": 7,
    "fr": 8,
    "fr-FR": 8,
    "de": 9,
    "de-DE": 9,
    "ja": 10,
    "ru": 11,
    "pt-BR": 12,
    "pt": 13,
    "ko": 14,
    "it": 15,
    "nl": 16,
    "pl": 17,
    "auto": 101,
}

DEFAULT_REPO_ID = "onnx-community/nemotron-3.5-asr-streaming-0.6b-onnx-int4"


def get_model_directory() -> str:
    """Retorna la ruta al directorio del modelo Nemotron ONNX.
    Si NEMOTRON_MODEL_DIR está definido, lo usa; de lo contrario, usa snapshot_download de HuggingFace.
    """
    custom_dir = os.getenv("NEMOTRON_MODEL_DIR")
    if custom_dir and os.path.isdir(custom_dir):
        return custom_dir

    # Busca en snapshot de Hugging Face
    logger.info(f"Localizando modelo {DEFAULT_REPO_ID}...")
    model_dir = snapshot_download(repo_id=DEFAULT_REPO_ID)
    return model_dir


class NemotronSTT(stt.STT):
    """Proveedor STT 100% local en streaming usando Nemotron-3.5-ASR (INT4 ONNX)."""

    def __init__(
        self,
        *,
        model_dir: str | None = None,
        language: str = "es-419",
    ) -> None:
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=True, interim_results=True)
        )
        self._language = language
        self._model_dir = model_dir or get_model_directory()

        logger.info(f"Cargando modelo Nemotron ONNX desde: {self._model_dir}")
        self._model = og.Model(self._model_dir)
        self._tokenizer = og.Tokenizer(self._model)
        self._params = og.GeneratorParams(self._model)
        logger.info("Modelo Nemotron STT cargado exitosamente.")

    @property
    def model(self) -> str:
        return "nemotron-3.5-asr-streaming-0.6b-onnx-int4"

    @property
    def provider(self) -> str:
        return "nvidia-onnx"

    @property
    def og_model(self) -> og.Model:
        return self._model

    @property
    def og_tokenizer(self) -> og.Tokenizer:
        return self._tokenizer

    @property
    def og_params(self) -> og.GeneratorParams:
        return self._params

    def get_lang_id(self, lang: str | None) -> int:
        if not lang:
            lang = self._language
        return LANG_TO_ID.get(lang, LANG_TO_ID.get(self._language, 3))

    def stream(
        self,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.RecognizeStream:
        lang = language if isinstance(language, str) else self._language
        return NemotronStream(
            stt_instance=self,
            conn_options=conn_options,
            language=lang,
        )

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        """Transcripción batch para buffers completos."""
        lang = language if isinstance(language, str) else self._language
        lang_id = self.get_lang_id(lang)

        # Resamplea audio a 16kHz float32
        resampler = rtc.AudioResampler(
            input_rate=buffer.sample_rate,
            output_rate=16000,
            quality=rtc.AudioResamplerQuality.HIGH,
        )
        resampled_frames = resampler.push(buffer)
        audio_data = bytearray()
        for f in resampled_frames:
            audio_data.extend(f.data)
        for f in resampler.flush():
            audio_data.extend(f.data)

        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

        def _batch_inference():
            processor = og.StreamingProcessor(self._model)
            processor.set_option("use_vad", "false")
            generator = og.Generator(self._model, self._params)
            tok_stream = self._tokenizer.create_stream()

            text = ""
            chunk_size = 8960  # 560ms a 16kHz
            for s in range(0, len(samples), chunk_size):
                sub_chunk = samples[s : s + chunk_size]
                inputs = processor.process(sub_chunk)
                if inputs is not None:
                    inputs["lang_id"] = np.array([lang_id], dtype=np.int32)
                    generator.set_inputs(inputs)
                    while not generator.is_done():
                        generator.generate_next_token()
                        toks = generator.get_next_tokens()
                        if len(toks) > 0:
                            t = tok_stream.decode(toks[0])
                            if t:
                                text += t

            flush_inputs = processor.flush()
            if flush_inputs is not None:
                flush_inputs["lang_id"] = np.array([lang_id], dtype=np.int32)
                generator.set_inputs(flush_inputs)
                while not generator.is_done():
                    generator.generate_next_token()
                    toks = generator.get_next_tokens()
                    if len(toks) > 0:
                        t = tok_stream.decode(toks[0])
                        if t:
                            text += t
            return text.strip()

        transcribed = await asyncio.to_thread(_batch_inference)
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(
                    language=lang,
                    text=transcribed,
                    start_time=0.0,
                    end_time=len(samples) / 16000.0,
                    confidence=1.0,
                )
            ],
        )


class NemotronStream(stt.RecognizeStream):
    """Flujo de reconocimiento continuo para sesiones WebRTC en tiempo real."""

    def __init__(
        self,
        *,
        stt_instance: NemotronSTT,
        conn_options: APIConnectOptions,
        language: str,
    ) -> None:
        super().__init__(
            stt=stt_instance,
            conn_options=conn_options,
            sample_rate=16000,
        )
        self._stt_instance = stt_instance
        self._language = language
        self._lang_id = stt_instance.get_lang_id(language)

    async def _run(self) -> None:
        model = self._stt_instance.og_model
        tokenizer = self._stt_instance.og_tokenizer
        params = self._stt_instance.og_params

        # Inicializa estado del procesador y generador para este stream
        processor = og.StreamingProcessor(model)
        processor.set_option("use_vad", "false")
        generator = og.Generator(model, params)
        tok_stream = tokenizer.create_stream()

        accumulated_text = ""
        speech_start_time = time.time()

        def _step_generator(inputs) -> str:
            inputs["lang_id"] = np.array([self._lang_id], dtype=np.int32)
            generator.set_inputs(inputs)
            new_text = ""
            while not generator.is_done():
                generator.generate_next_token()
                toks = generator.get_next_tokens()
                if len(toks) > 0:
                    t = tok_stream.decode(toks[0])
                    if t:
                        new_text += t
            return new_text

        try:
            async for item in self._input_ch:
                if isinstance(item, stt.RecognizeStream._FlushSentinel):
                    # Fin de segmento / turno de habla
                    flush_inputs = processor.flush()
                    if flush_inputs is not None:
                        flushed_text = await asyncio.to_thread(_step_generator, flush_inputs)
                        if flushed_text:
                            accumulated_text += flushed_text

                    clean_text = accumulated_text.strip()
                    if clean_text:
                        self._event_ch.send_nowait(
                            stt.SpeechEvent(
                                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                                alternatives=[
                                    stt.SpeechData(
                                        language=self._language,
                                        text=clean_text,
                                        start_time=speech_start_time,
                                        end_time=time.time(),
                                        confidence=1.0,
                                    )
                                ],
                            )
                        )
                    # Reiniciar estado para la siguiente frase
                    accumulated_text = ""
                    speech_start_time = time.time()
                    generator = og.Generator(model, params)
                    processor = og.StreamingProcessor(model)
                    processor.set_option("use_vad", "false")
                    tok_stream = tokenizer.create_stream()

                elif isinstance(item, rtc.AudioFrame):
                    # Conversión de audio frame PCM a float32 normalizado
                    samples = (
                        np.frombuffer(item.data, dtype=np.int16).astype(np.float32)
                        / 32768.0
                    )
                    inputs = processor.process(samples)
                    if inputs is not None:
                        new_chunk_text = await asyncio.to_thread(_step_generator, inputs)
                        if new_chunk_text:
                            accumulated_text += new_chunk_text
                            clean_interim = accumulated_text.strip()
                            if clean_interim:
                                self._event_ch.send_nowait(
                                    stt.SpeechEvent(
                                        type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                                        alternatives=[
                                            stt.SpeechData(
                                                language=self._language,
                                                text=clean_interim,
                                                start_time=speech_start_time,
                                                end_time=time.time(),
                                                confidence=1.0,
                                            )
                                        ],
                                    )
                                )

            # Procesar residuo al cerrar el canal de entrada
            flush_inputs = processor.flush()
            if flush_inputs is not None:
                flushed_text = await asyncio.to_thread(_step_generator, flush_inputs)
                if flushed_text:
                    accumulated_text += flushed_text

            clean_text = accumulated_text.strip()
            if clean_text:
                self._event_ch.send_nowait(
                    stt.SpeechEvent(
                        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                        alternatives=[
                            stt.SpeechData(
                                language=self._language,
                                text=clean_text,
                                start_time=speech_start_time,
                                end_time=time.time(),
                                confidence=1.0,
                            )
                        ],
                    )
                )

        except Exception as e:
            logger.error(f"Error en stream de reconocimiento Nemotron: {e}", exc_info=True)
            raise
