"""Protocolo VVA1 del receptor de voz del avatar (plugin VivaAvatar de Unreal).

Portado de `Plugins/VivaAvatar/Source/VivaAvatar/Private/VivaAvatarReceiver.cpp`:

* Mensajes de control: texto JSON (<= 4096 caracteres) con `version` = 1 y el
  `session_id` del saludo `ready`.
* Audio: tramos binarios con cabecera de 44 bytes
  ``b"VVA1" | session(16) | utterance(16) | offset_en_muestras(u64 BE)``
  seguida de PCM s16le, 48 kHz, mono.
* Los GUID viajan como los 16 bytes big-endian del UUID textual.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

VERSION = 1
MAGIC = b"VVA1"
HEADER_SIZE = 44
SAMPLE_RATE = 48000
CHANNELS = 1
ENCODING = "pcm_s16le"
BYTES_PER_SAMPLE = 2

# Limites del receptor: un paquete no puede pasar de 192044 bytes y el buffer
# pendiente (recibido - reproducido) no puede pasar de 96000 muestras.
MAX_PACKET_BYTES = 192044
MAX_PENDING_SAMPLES = 96000
MAX_CONTROL_CHARS = 4096

# Estados que acepta el receptor. "speaking" lo ignora: lo deriva del audio.
VALID_STATES = frozenset(
    {
        "idle",
        "listening",
        "thinking",
        "speaking",
        "celebrating",
        "warning",
        "connecting",
        "escalating",
    }
)


def encode_audio_packet(
    session: uuid.UUID, utterance: uuid.UUID, offset_samples: int, pcm: bytes
) -> bytes:
    """Arma un tramo binario VVA1. `pcm` debe ser s16le, no vacio y de largo par."""
    if not pcm or len(pcm) % BYTES_PER_SAMPLE:
        raise ValueError("el PCM debe tener al menos una muestra completa")
    packet = (
        MAGIC
        + session.bytes
        + utterance.bytes
        + offset_samples.to_bytes(8, "big")
        + pcm
    )
    if len(packet) > MAX_PACKET_BYTES:
        raise ValueError("paquete VVA1 demasiado grande")
    return packet


@dataclass(frozen=True)
class AudioPacket:
    session: uuid.UUID
    utterance: uuid.UUID
    offset: int
    pcm: bytes


def decode_audio_packet(packet: bytes) -> AudioPacket:
    """Inversa de `encode_audio_packet` (la usa el Unreal simulado de las pruebas)."""
    if (
        len(packet) <= HEADER_SIZE
        or (len(packet) - HEADER_SIZE) % BYTES_PER_SAMPLE
        or packet[:4] != MAGIC
    ):
        raise ValueError("Invalid PCM frame")
    return AudioPacket(
        session=uuid.UUID(bytes=packet[4:20]),
        utterance=uuid.UUID(bytes=packet[20:36]),
        offset=int.from_bytes(packet[36:44], "big"),
        pcm=packet[HEADER_SIZE:],
    )


def _control(kind: str, session: uuid.UUID, **fields: object) -> str:
    message = {"type": kind, "version": VERSION, "session_id": str(session), **fields}
    text = json.dumps(message, separators=(",", ":"))
    if len(text) > MAX_CONTROL_CHARS:
        raise ValueError("mensaje de control demasiado largo")
    return text


def ready(session: uuid.UUID) -> str:
    return _control("ready", session)


def state_changed(session: uuid.UUID, state: str) -> str:
    if state not in VALID_STATES:
        raise ValueError(f"estado invalido: {state}")
    return _control("state_changed", session, state=state)


def audio_start(session: uuid.UUID, utterance: uuid.UUID) -> str:
    return _control(
        "audio_start",
        session,
        utterance_id=str(utterance),
        sample_rate=SAMPLE_RATE,
        channels=CHANNELS,
        encoding=ENCODING,
    )


def audio_end(session: uuid.UUID, utterance: uuid.UUID, total_samples: int) -> str:
    return _control(
        "audio_end", session, utterance_id=str(utterance), total_samples=total_samples
    )


def cancel(session: uuid.UUID, utterance: uuid.UUID) -> str:
    return _control("cancel", session, utterance_id=str(utterance))
