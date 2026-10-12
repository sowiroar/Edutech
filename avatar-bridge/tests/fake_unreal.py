"""Unreal simulado: port estricto del receptor `UVivaAvatarReceiver` (C++).

Reproduce sus reglas de validacion, sus limites y su orden de proceso (por cada
tick de ~20 ms, primero todos los textos y luego todos los binarios), y reporta
cada violacion en `violations` cerrando con 1008 como hace `Fail()`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from collections.abc import Callable

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

import vva1

TICK = 0.02
PRIME_SAMPLES = 1920
STALL_SECONDS = 5.0
VALID_STATES = vva1.VALID_STATES
VALID_CHARACTERS = vva1.VALID_CHARACTERS


class FakeUnreal:
    def __init__(self, url: str, play_speed: float = 20.0) -> None:
        self.url = url
        self.play_speed = play_speed  # 1.0 = tiempo real
        self.violations: list[str] = []
        self.states: list[str] = []
        self.characters: list[str] = []
        self.finished: list[tuple[uuid.UUID, int]] = []
        self.cleared: list[uuid.UUID] = []
        self.audio: dict[uuid.UUID, bytearray] = {}
        self.session: uuid.UUID | None = None
        self.close_code: int | None = None
        self.ws = None
        self._task: asyncio.Task[None] | None = None
        self._texts: list[str] = []
        self._binaries: list[bytes] = []
        self._reset_utterance()
        self._seen: set[uuid.UUID] = set()
        self._cancelled = True
        self._finished_reported = False
        self._last_message = time.monotonic()
        self._render_credit = 0.0
        self._last_reported = 0

    def _reset_utterance(self) -> None:
        self.utterance: uuid.UUID | None = None
        self.received = 0
        self.rendered = 0
        self.expected_total = 0
        self.end_declared = False
        self.ended = False
        self.primed = False
        self.started_reported = False
        self._last_reported = 0

    # -- ciclo de vida ------------------------------------------------------------

    async def start(self) -> None:
        self.ws = await connect(self.url, compression=None)
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self.ws is not None:
            await self.ws.close()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, ConnectionClosed):
                await self._task

    async def wait_for(
        self, predicate: Callable[[], bool], timeout: float = 5.0
    ) -> None:
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"condicion no cumplida; violaciones={self.violations}"
                )
            await asyncio.sleep(0.01)

    # -- bucle principal ----------------------------------------------------------

    async def _run(self) -> None:
        reader = asyncio.create_task(self._collect())
        try:
            while not reader.done():
                await asyncio.sleep(TICK)
                await self._tick()
        finally:
            reader.cancel()

    async def _collect(self) -> None:
        try:
            async for message in self.ws:
                if isinstance(message, str):
                    self._texts.append(message)
                else:
                    self._binaries.append(message)
        except ConnectionClosed:
            pass
        finally:
            self.close_code = self.ws.close_code if self.ws else None

    async def _tick(self) -> None:
        texts, self._texts = self._texts, []
        binaries, self._binaries = self._binaries, []
        for text in texts:  # el receptor real procesa los textos antes que los binarios
            await self._handle_control(text)
        for packet in binaries:
            await self._handle_binary(packet)
        await self._advance_playback()

    async def _fail(self, reason: str) -> None:
        self.violations.append(reason)
        await self.ws.close(1008, reason[:100])

    async def _send_ack(self, kind: str, samples: int = 0) -> None:
        # FGuid::ToString(DigitsWithHyphens) del receptor real siempre da mayusculas.
        message = {"version": 1, "type": kind, "session_id": str(self.session).upper()}
        if kind != "ready":
            message["utterance_id"] = str(self.utterance).upper()
            message["played_samples"] = samples
        await self.ws.send(json.dumps(message))

    # -- HandleControl ------------------------------------------------------------

    async def _handle_control(self, text: str) -> None:
        if len(text) > vva1.MAX_CONTROL_CHARS:
            return await self._fail("Invalid control JSON")
        try:
            obj = json.loads(text)
            kind = obj["type"]
            if obj["version"] != 1:
                raise ValueError
            incoming = uuid.UUID(obj["session_id"])
        except (ValueError, KeyError, TypeError):
            return await self._fail("Invalid control envelope")
        self._last_message = time.monotonic()
        if kind == "ready":
            if self.session is not None:
                return await self._fail("Duplicate handshake")
            self.session = incoming
            await self._send_ack("ready")
            self.states.append("idle")
            return
        if self.session != incoming:
            return await self._fail("Foreign session")
        if kind == "state_changed":
            if obj.get("state") not in VALID_STATES:
                return await self._fail("Invalid state")
            if obj["state"] != "speaking":
                self.states.append(obj["state"])
            return
        if kind == "character_changed":
            if obj.get("name") not in VALID_CHARACTERS:
                return await self._fail("Invalid character")
            self.characters.append(obj["name"])
            return
        try:
            utterance = uuid.UUID(obj["utterance_id"])
        except (ValueError, KeyError, TypeError):
            return await self._fail("Missing utterance ID")
        if kind == "audio_start":
            if (
                obj.get("sample_rate") != 48000
                or obj.get("channels") != 1
                or obj.get("encoding") != "pcm_s16le"
            ):
                return await self._fail("Receiver requires 48kHz mono PCM16")
            if utterance in self._seen or (
                not self._cancelled and not self._finished_reported
            ):
                return await self._fail("Overlapping or reused utterance")
            self._reset_utterance()
            self.utterance = utterance
            self._seen.add(utterance)
            self.audio[utterance] = bytearray()
            self._cancelled = False
            self._finished_reported = False
            return
        if utterance != self.utterance:
            return
        if kind == "cancel":
            self._cancelled = True
            count = self.rendered
            await self._send_ack("playback_cleared", count)
            self.cleared.append(utterance)
            self.states.append("listening")
            return
        if kind == "audio_end":
            if self._cancelled:
                return
            total = obj.get("total_samples")
            if (
                not isinstance(total, int)
                or self.end_declared
                or total < self.received
                or total - self.received > vva1.MAX_PENDING_SAMPLES
            ):
                return await self._fail("End count mismatch")
            self.expected_total = total
            self.end_declared = True
            self.ended = self.received == total
            return
        await self._fail("Unknown control message")

    # -- HandleBinary -------------------------------------------------------------

    async def _handle_binary(self, packet: bytes) -> None:
        if len(packet) > vva1.MAX_PACKET_BYTES:
            return await self._fail("Oversized audio packet")
        try:
            decoded = vva1.decode_audio_packet(packet)
        except ValueError:
            return await self._fail("Invalid PCM frame")
        if decoded.session != self.session:
            return await self._fail("Foreign audio session")
        if decoded.utterance != self.utterance or self._cancelled:
            return
        self._last_message = time.monotonic()
        count = len(decoded.pcm) // 2
        if (
            decoded.offset != self.received
            or self.ended
            or (self.end_declared and self.received + count > self.expected_total)
        ):
            return await self._fail("Audio offset or end violation")
        if self.received + count - self.rendered > vva1.MAX_PENDING_SAMPLES:
            return await self._fail("Audio buffer full")
        self.audio[decoded.utterance] += decoded.pcm
        self.received += count
        if self.end_declared and self.received == self.expected_total:
            self.ended = True

    # -- reproduccion simulada (OnGenerateAudio + TickComponent) ---------------------

    async def _advance_playback(self) -> None:
        if self._cancelled or self.utterance is None:
            return
        if not self.primed and (
            self.received - self.rendered >= PRIME_SAMPLES or self.ended
        ):
            self.primed = True
        if self.primed:
            self._render_credit += TICK * vva1.SAMPLE_RATE * self.play_speed
            step = int(self._render_credit)
            self._render_credit -= step
            self.rendered += min(step, self.received - self.rendered)
        if (
            not self._finished_reported
            and time.monotonic() - self._last_message > STALL_SECONDS
        ):
            return await self._fail("Audio stream stalled for more than 5 seconds")
        if self.rendered > 0 and not self.started_reported:
            self.started_reported = True
            await self._send_ack("playback_started", self.rendered)
            self.states.append("speaking")
        if self.rendered != self._last_reported:
            self._last_reported = self.rendered
            await self._send_ack("playback_progress", self.rendered)
        if (
            self.ended
            and self.rendered == self.received
            and not self._finished_reported
        ):
            self._finished_reported = True
            await self._send_ack("playback_finished", self.rendered)
            self.finished.append((self.utterance, self.rendered))
            self.states.append("idle")
