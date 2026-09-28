"""Conexion con un Unreal (cliente) que habla VVA1."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from typing import Protocol

import vva1

logger = logging.getLogger("avatar-bridge.link")

# Cuanto audio puede ir por delante de lo ya reproducido. Debe quedar por debajo
# del limite del receptor (96000 muestras) y ser corto para que, si el usuario
# interrumpe, el avatar no siga hablando mucho rato.
LEAD_CAP_SAMPLES = vva1.SAMPLE_RATE * 3 // 2
# Tamano maximo de cada tramo binario (100 ms).
MAX_CHUNK_SAMPLES = vva1.SAMPLE_RATE // 10
HANDSHAKE_TIMEOUT = 5.0
PROGRESS_TIMEOUT = 2.0
IDLE_TIMEOUT = 10.0
CANCEL_TIMEOUT = 2.0


class Socket(Protocol):
    async def send(self, message: str | bytes) -> None: ...
    def __aiter__(self): ...


class UnrealLink:
    """Una conexion WebSocket con el receptor de Unreal, con su sesion VVA1."""

    def __init__(self, ws: Socket, session: uuid.UUID | None = None) -> None:
        self.ws = ws
        self.session = session or uuid.uuid4()
        self.played = 0
        self._sent = 0
        self._utterance: uuid.UUID | None = None
        self._ready = asyncio.Event()
        self._idle = asyncio.Event()
        self._idle.set()
        self._progress = asyncio.Event()
        self._deferred_state: str | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def active(self) -> bool:
        """Hay un enunciado enviado que Unreal aun no termina de reproducir."""
        return self._utterance is not None

    # -- entrada: avisos de Unreal ------------------------------------------------

    async def read_loop(self) -> None:
        """Procesa los avisos de Unreal hasta que se cierre la conexion."""
        async for message in self.ws:
            if isinstance(message, str):
                self._on_control(message)

    def _on_control(self, text: str) -> None:
        try:
            message = json.loads(text)
            kind = message["type"]
            # Unreal siempre devuelve los GUID en mayusculas (DigitsWithHyphens);
            # comparar como uuid.UUID en vez de texto crudo evita que eso se
            # confunda con una sesion/enunciado distinto.
            session = uuid.UUID(message["session_id"])
        except (ValueError, KeyError, TypeError):
            logger.warning("Mensaje de Unreal ilegible: %.120s", text)
            return
        if session != self.session:
            logger.warning("Aviso de una sesion ajena: %s", session)
            return
        if kind == "ready":
            self._ready.set()
            return
        utterance_id = message.get("utterance_id")
        try:
            if self._utterance is None or uuid.UUID(utterance_id) != self._utterance:
                return  # aviso rezagado de un enunciado que ya no es el actual
        except (ValueError, TypeError):
            return
        played = message.get("played_samples")
        if isinstance(played, int):
            self.played = played
        if kind == "playback_progress":
            self._progress.set()
        elif kind in ("playback_finished", "playback_cleared"):
            self._finish()

    def _finish(self) -> None:
        self._utterance = None
        self._idle.set()
        self._progress.set()
        if self._deferred_state is not None:
            self._spawn(self._flush_state())

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _flush_state(self) -> None:
        state, self._deferred_state = self._deferred_state, None
        if state is not None:
            with contextlib.suppress(Exception):
                await self.ws.send(vva1.state_changed(self.session, state))

    # -- salida: ordenes hacia Unreal ---------------------------------------------

    async def handshake(self) -> None:
        """Envia `ready` y espera el acuse (el receptor lo exige una sola vez)."""
        await self.ws.send(vva1.ready(self.session))
        await asyncio.wait_for(self._ready.wait(), HANDSHAKE_TIMEOUT)

    async def set_state(self, state: str) -> None:
        if state == "speaking":
            return  # Unreal lo deduce del audio que reproduce
        if self.active:
            # No cambiar la pose mientras aun suena el final de la frase.
            self._deferred_state = state
            return
        await self.ws.send(vva1.state_changed(self.session, state))

    async def open_utterance(self) -> None:
        try:
            await asyncio.wait_for(self._idle.wait(), IDLE_TIMEOUT)
        except TimeoutError:
            logger.warning("Unreal no termino el enunciado anterior; se cancela")
            await self.cancel()
        utterance = uuid.uuid4()
        self._utterance = utterance
        self._sent = 0
        self.played = 0
        self._idle.clear()
        await self.ws.send(vva1.audio_start(self.session, utterance))

    async def push(self, pcm: bytes) -> None:
        step = MAX_CHUNK_SAMPLES * vva1.BYTES_PER_SAMPLE
        for start in range(0, len(pcm) - len(pcm) % 2, step):
            await self._push_chunk(pcm[start : start + step])

    async def _push_chunk(self, chunk: bytes) -> None:
        utterance = self._utterance
        if utterance is None:
            return
        while self._sent - self.played > LEAD_CAP_SAMPLES:
            self._progress.clear()
            try:
                await asyncio.wait_for(self._progress.wait(), PROGRESS_TIMEOUT)
            except TimeoutError:
                logger.warning("Unreal no avanza; se cancela el enunciado")
                await self.cancel()
                return
            if self._utterance != utterance:
                return
        packet = vva1.encode_audio_packet(self.session, utterance, self._sent, chunk)
        await self.ws.send(packet)
        self._sent += len(chunk) // vva1.BYTES_PER_SAMPLE

    async def end_utterance(self) -> None:
        utterance = self._utterance
        if utterance is None:
            return
        await self.ws.send(vva1.audio_end(self.session, utterance, self._sent))

    async def cancel(self) -> None:
        utterance = self._utterance
        if utterance is None:
            return
        await self.ws.send(vva1.cancel(self.session, utterance))
        try:
            await asyncio.wait_for(self._idle.wait(), CANCEL_TIMEOUT)
        except TimeoutError:
            self._finish()  # Unreal no contesto: se olvida el enunciado
