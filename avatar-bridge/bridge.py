"""Une el audio/estado del agente (LiveKit) con el enlace VVA1 hacia Unreal."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from websockets.exceptions import ConnectionClosed

from link import UnrealLink
from segmenter import End, Pcm, Segmenter, Start

logger = logging.getLogger("avatar-bridge")

# Estado `lk.agent.state` de LiveKit -> estado del receptor de Unreal.
# "speaking" no se envia: Unreal lo deduce del audio que reproduce.
AGENT_STATE_TO_AVATAR = {
    "initializing": "connecting",
    "idle": "idle",
    "listening": "listening",
    "thinking": "thinking",
}


class Bridge:
    def __init__(
        self,
        segmenter: Segmenter | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.link: UnrealLink | None = None
        self._segmenter = segmenter or Segmenter()
        self._clock = clock
        self._lock = asyncio.Lock()

    def attach(self, link: UnrealLink) -> None:
        self.link = link
        self._segmenter.reset()
        logger.info("Unreal conectado (sesion %s)", link.session)

    def detach(self, link: UnrealLink) -> None:
        if self.link is link:
            self.link = None
            self._segmenter.reset()
            logger.info("Unreal desconectado")

    async def on_frame(self, pcm: bytes) -> None:
        """Tramo PCM (48 kHz mono s16le) del audio del agente."""
        async with self._lock:
            link = self.link
            if link is not None:
                await self._apply(link, self._segmenter.feed(pcm, self._clock()))

    async def on_tick(self) -> None:
        """Llamar a menudo: cierra el enunciado cuando el agente calla."""
        async with self._lock:
            link = self.link
            if link is not None:
                await self._apply(link, self._segmenter.tick(self._clock()))

    async def on_agent_state(self, state: str) -> None:
        avatar_state = AGENT_STATE_TO_AVATAR.get(state)
        link = self.link
        if avatar_state is None or link is None:
            return
        try:
            await link.set_state(avatar_state)
        except ConnectionClosed:
            self.detach(link)

    async def _apply(self, link: UnrealLink, events) -> None:
        try:
            for event in events:
                if isinstance(event, Start):
                    await link.open_utterance()
                elif isinstance(event, Pcm):
                    await link.push(event.data)
                elif isinstance(event, End):
                    await link.end_utterance()
        except ConnectionClosed:
            self.detach(link)
