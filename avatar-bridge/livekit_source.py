"""Origen de audio y estado: sigue al agente en la sala de LiveKit Cloud.

El frontend crea una sala nueva por sesion (`voice_assistant_room_NNNN`) y el
agente entra a ella. Este modulo busca la sala activa (con un agente y una
persona), se une como participante oculto y de solo lectura, y reenvia el audio
y el estado (`lk.agent.state`) del agente al `Bridge`. Solo trabaja mientras hay
un Unreal conectado.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from livekit import api, rtc

from bridge import Bridge

logger = logging.getLogger("avatar-bridge.livekit")

BRIDGE_IDENTITY = "avatar-bridge"
ATTRIBUTE_AGENT_STATE = "lk.agent.state"
AGENT = rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
STANDARD = rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD


def api_url(livekit_url: str) -> str:
    """La API REST usa http(s); el cliente de tiempo real usa ws(s)."""
    if livekit_url.startswith("wss://"):
        return "https://" + livekit_url[len("wss://") :]
    if livekit_url.startswith("ws://"):
        return "http://" + livekit_url[len("ws://") :]
    return livekit_url


class RoomFollower:
    def __init__(
        self,
        bridge: Bridge,
        url: str,
        api_key: str,
        api_secret: str,
        # Red de seguridad, no el mecanismo principal: la ruta rapida es
        # hint() (ver mas abajo), que el frontend dispara al crear la sala.
        # Bajarlo a 0.2s (commit anterior) para que el puente alcanzara a
        # suscribirse antes de que Lira terminara su saludo funciono, pero
        # a costa de golpear list_rooms() ~5 veces por segundo todo el dia,
        # incluso sin ninguna llamada activa — eso agoto el limite de tasa
        # de LiveKit Cloud y bloqueo el WebSocket real de los usuarios
        # (error 429 al conectar). Con hint() el poll vuelve a ser solo un
        # respaldo por si el aviso directo falla (Claude, 2026-09-29).
        poll_seconds: float = 2.0,
    ) -> None:
        self._bridge = bridge
        self._url = url
        self._key = api_key
        self._secret = api_secret
        self._poll = poll_seconds
        self._room: rtc.Room | None = None
        self._readers: dict[str, asyncio.Task[None]] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._hint_event = asyncio.Event()

    def hint(self) -> None:
        """Despierta el bucle de inmediato en vez de esperar al proximo poll.
        Lo llama el endpoint /hint cuando el frontend crea una sala nueva."""
        self._hint_event.set()

    # El motor de LiveKit (Rust, por debajo de rtc.Room) a veces se queda
    # reconectando en silencio tras un "ping timeout" y nunca vuelve: room.
    # connect()/disconnect() se cuelgan para siempre y _step() no regresa,
    # dejando el bucle entero trabado (sin excepcion que loguear) y al avatar
    # sin audio indefinidamente. El limite de abajo garantiza que el bucle
    # siempre avanza: si un paso se demora demasiado, lo cancelamos y
    # soltamos la sala vieja para volver a intentarlo desde cero en el
    # siguiente ciclo (Claude, 2026-09-28).
    _STEP_TIMEOUT = 10.0

    async def run(self) -> None:
        async with api.LiveKitAPI(
            url=api_url(self._url), api_key=self._key, api_secret=self._secret
        ) as lkapi:
            while True:
                try:
                    await asyncio.wait_for(self._step(lkapi), timeout=self._STEP_TIMEOUT)
                except asyncio.CancelledError:
                    await self._leave()
                    raise
                except TimeoutError:
                    logger.warning(
                        "El seguimiento de la sala no respondio en %ss; "
                        "se abandona la conexion y se reintenta desde cero",
                        self._STEP_TIMEOUT,
                    )
                    self._force_reset()
                except Exception:
                    logger.exception("Fallo al seguir la sala de LiveKit")
                # Espera hasta self._poll, pero se despierta antes si llega un
                # hint() — así el caso común (aviso directo) es instantáneo y
                # el poll de fondo casi nunca se ejecuta de verdad.
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._hint_event.wait(), timeout=self._poll)
                self._hint_event.clear()

    async def _step(self, lkapi: api.LiveKitAPI) -> None:
        if self._bridge.link is None:
            await self._leave()  # sin Unreal no hace falta estar en ninguna sala
            return
        if self._room is not None:
            humans = [
                p for p in self._room.remote_participants.values() if p.kind == STANDARD
            ]
            if (
                not humans
                or self._room.connection_state != rtc.ConnectionState.CONN_CONNECTED
            ):
                await self._leave()  # la persona se fue: liberar la sala
            return
        name = await self._find_room(lkapi)
        if name is not None:
            await self._join(name)

    async def _find_room(self, lkapi: api.LiveKitAPI) -> str | None:
        rooms = (await lkapi.room.list_rooms(api.ListRoomsRequest())).rooms
        for room in sorted(rooms, key=lambda r: r.creation_time, reverse=True):
            listing = await lkapi.room.list_participants(
                api.ListParticipantsRequest(room=room.name)
            )
            participants = listing.participants
            has_agent = any(p.kind == AGENT for p in participants)
            has_human = any(
                p.kind == STANDARD and p.identity != BRIDGE_IDENTITY
                for p in participants
            )
            if has_agent and has_human:
                return room.name
        return None

    async def _join(self, room_name: str) -> None:
        token = (
            api.AccessToken(self._key, self._secret)
            .with_identity(BRIDGE_IDENTITY)
            .with_name("Avatar bridge")
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_subscribe=True,
                    can_publish=False,
                    can_publish_data=False,
                    hidden=True,
                )
            )
            .to_jwt()
        )
        room = rtc.Room()
        room.on("track_subscribed", self._on_track_subscribed)
        room.on("track_unsubscribed", self._on_track_unsubscribed)
        room.on("participant_attributes_changed", self._on_attributes_changed)
        await room.connect(self._url, token)
        self._room = room
        logger.info("Siguiendo la sala %s", room_name)
        for participant in room.remote_participants.values():
            if participant.kind == AGENT:
                self._forward_state(participant)

    async def _leave(self) -> None:
        room, self._room = self._room, None
        for task in self._readers.values():
            task.cancel()
        self._readers.clear()
        if room is not None:
            with contextlib.suppress(Exception):
                await room.disconnect()
            logger.info("Sala liberada")

    def _force_reset(self) -> None:
        """Como _leave(), pero sin awaits: para cuando la sala ya esta
        colgada y esperar su respuesta es justo lo que hay que evitar. El
        objeto Room viejo se abandona (no se cierra activamente) y su
        limpieza queda para el recolector de basura."""
        for task in self._readers.values():
            task.cancel()
        self._readers.clear()
        self._room = None

    # -- eventos de la sala (llamadas sincronas) ------------------------------------

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _on_track_subscribed(
        self,
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ) -> None:
        if participant.kind != AGENT or track.kind != rtc.TrackKind.KIND_AUDIO:
            return
        logger.info("Audio del agente %s suscrito", participant.identity)
        self._forward_state(participant)
        self._readers[track.sid] = asyncio.create_task(self._read_audio(track))

    def _on_track_unsubscribed(
        self,
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ) -> None:
        task = self._readers.pop(track.sid, None)
        if task is not None:
            task.cancel()

    def _on_attributes_changed(
        self, changed: dict[str, str], participant: rtc.Participant
    ) -> None:
        if participant.kind == AGENT and ATTRIBUTE_AGENT_STATE in changed:
            self._forward_state(participant)

    def _forward_state(self, participant: rtc.Participant) -> None:
        state = participant.attributes.get(ATTRIBUTE_AGENT_STATE)
        if state:
            self._spawn(self._bridge.on_agent_state(state))

    async def _read_audio(self, track: rtc.Track) -> None:
        stream = rtc.AudioStream(
            track, sample_rate=48000, num_channels=1, frame_size_ms=20
        )
        try:
            async for event in stream:
                await self._bridge.on_frame(bytes(event.frame.data))
        finally:
            await stream.aclose()
