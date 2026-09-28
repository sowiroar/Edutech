"""Divide el audio continuo del agente en enunciados (`utterance`) para VVA1.

El receptor de Unreal exige un `audio_start` ... `audio_end` por cada tramo de
habla y no admite enunciados solapados. LiveKit entrega el audio del agente como
un flujo de tramos de 10-20 ms (a veces sin tramos mientras calla), asi que hay
que decidir aqui cuando empieza y cuando termina cada intervencion.
"""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Literal

# Pico minimo (de 32768) para considerar que un tramo tiene voz: ~ -40 dBFS.
DEFAULT_VOICE_PEAK = 300
# Silencio continuo que cierra un enunciado. Debe ser bastante menor que los
# 5 s tras los que el receptor da por colgado un enunciado sin audio nuevo.
DEFAULT_SILENCE_SECONDS = 0.6


@dataclass(frozen=True)
class Start:
    kind: Literal["start"] = "start"


@dataclass(frozen=True)
class Pcm:
    data: bytes
    kind: Literal["pcm"] = "pcm"


@dataclass(frozen=True)
class End:
    kind: Literal["end"] = "end"


Event = Start | Pcm | End


def peak(pcm: bytes) -> int:
    """Pico absoluto de un bloque PCM s16le."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    return max(map(abs, samples), default=0)


class Segmenter:
    def __init__(
        self,
        voice_peak: int = DEFAULT_VOICE_PEAK,
        silence_seconds: float = DEFAULT_SILENCE_SECONDS,
    ) -> None:
        self.voice_peak = voice_peak
        self.silence_seconds = silence_seconds
        self._open = False
        self._last_voice = 0.0
        self._last_frame = 0.0

    @property
    def is_open(self) -> bool:
        return self._open

    def reset(self) -> None:
        self._open = False

    def feed(self, pcm: bytes, now: float) -> list[Event]:
        """Procesa un tramo de audio recibido en el instante `now` (segundos)."""
        if not pcm:
            return []
        has_voice = peak(pcm) >= self.voice_peak
        events: list[Event] = []
        if not self._open:
            if not has_voice:
                return events  # silencio entre enunciados: no se envia nada
            self._open = True
            events.append(Start())
        events.append(Pcm(pcm))
        self._last_frame = now
        if has_voice:
            self._last_voice = now
        elif now - self._last_voice >= self.silence_seconds:
            self._open = False
            events.append(End())
        return events

    def tick(self, now: float) -> list[Event]:
        """Cierra el enunciado si dejaron de llegar tramos (el agente callo)."""
        if self._open and now - self._last_frame >= self.silence_seconds:
            self._open = False
            return [End()]
        return []
