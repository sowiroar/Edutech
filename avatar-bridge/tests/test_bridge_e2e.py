"""El puente completo (segmentador + enlace + servidor) contra un Unreal simulado."""

import asyncio
import json
from array import array

import pytest
from fake_unreal import FakeUnreal
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import link as link_module
from bridge import Bridge
from livekit_source import RoomFollower
from main import make_handler, make_process_request
from segmenter import Segmenter

FRAME_SAMPLES = 960  # 20 ms a 48 kHz


def tone_frames(seconds: float, amplitude: int = 8000) -> list[bytes]:
    count = round(seconds * 48000 / FRAME_SAMPLES)
    return [array("h", [amplitude] * FRAME_SAMPLES).tobytes() for _ in range(count)]


@pytest.fixture
async def stack():
    bridge = Bridge(Segmenter(silence_seconds=0.15))
    # No se conecta a LiveKit de verdad (.run() nunca se llama aqui); solo
    # hace falta la instancia para que /hint tenga a quien avisarle.
    follower = RoomFollower(bridge, url="wss://example.invalid", api_key="k", api_secret="s")
    server = await serve(
        make_handler(bridge),
        "127.0.0.1",
        0,
        compression=None,
        process_request=make_process_request(bridge, follower),
    )
    url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
    yield bridge, url
    server.close()
    await server.wait_closed()


async def connect_unreal(bridge, url, **kwargs) -> FakeUnreal:
    fake = FakeUnreal(url, **kwargs)
    await fake.start()
    await fake.wait_for(
        lambda: (
            fake.session is not None
            and bridge.link is not None
            and bridge.link.session == fake.session
        )
    )
    return fake


async def speak(bridge, seconds: float) -> bytes:
    frames = tone_frames(seconds)
    for frame in frames:
        await bridge.on_frame(frame)
    await asyncio.sleep(0.25)  # el agente calla: pasa la ventana de silencio
    await bridge.on_tick()
    return b"".join(frames)


async def test_one_utterance_reaches_unreal_intact(stack):
    bridge, url = stack
    fake = await connect_unreal(bridge, url)
    sent = await speak(bridge, 1.0)
    await fake.wait_for(lambda: len(fake.finished) == 1)
    utterance, samples = fake.finished[0]
    assert fake.violations == []
    assert samples == 48000
    assert bytes(fake.audio[utterance]) == sent
    assert fake.states[0] == "idle"
    assert "speaking" in fake.states
    await fake.stop()


async def test_consecutive_utterances_never_overlap(stack):
    bridge, url = stack
    fake = await connect_unreal(bridge, url)
    first = await speak(bridge, 0.5)
    second = await speak(bridge, 0.5)
    await fake.wait_for(lambda: len(fake.finished) == 2)
    assert fake.violations == []
    (id_a, _), (id_b, _) = fake.finished
    assert id_a != id_b
    assert bytes(fake.audio[id_a]) == first
    assert bytes(fake.audio[id_b]) == second
    await fake.stop()


async def test_burst_faster_than_playback_is_paced(stack):
    bridge, url = stack
    fake = await connect_unreal(bridge, url, play_speed=10.0)
    sent = await speak(
        bridge, 4.0
    )  # 4 s de audio de golpe: no debe desbordar el buffer
    await fake.wait_for(lambda: len(fake.finished) == 1, timeout=10)
    utterance, samples = fake.finished[0]
    assert fake.violations == []
    assert samples == 4 * 48000
    assert bytes(fake.audio[utterance]) == sent
    await fake.stop()


async def test_agent_state_forwarded_and_deferred_while_speaking(stack):
    bridge, url = stack
    fake = await connect_unreal(bridge, url, play_speed=1.0)
    await bridge.on_agent_state("thinking")
    await fake.wait_for(lambda: fake.states[-1] == "thinking")
    await bridge.on_agent_state("speaking")  # Unreal lo deduce del audio
    for frame in tone_frames(0.5):
        await bridge.on_frame(frame)
    await bridge.on_agent_state("listening")
    await asyncio.sleep(0.1)
    assert "listening" not in fake.states  # aun suena la frase: se difiere
    await asyncio.sleep(0.25)
    await bridge.on_tick()
    await fake.wait_for(lambda: fake.states[-2:] == ["idle", "listening"])
    assert fake.violations == []
    await fake.stop()


async def test_agent_character_forwarded_and_deferred_while_speaking(stack):
    bridge, url = stack
    fake = await connect_unreal(bridge, url, play_speed=1.0)
    await bridge.on_agent_character("LIRA")
    await fake.wait_for(lambda: fake.characters == ["LIRA"])
    for frame in tone_frames(0.5):
        await bridge.on_frame(frame)
    await bridge.on_agent_character("ELIAN")  # el enunciado de LIRA aun suena
    await asyncio.sleep(0.1)
    assert fake.characters == ["LIRA"]  # se difiere: no cambia a media frase
    await asyncio.sleep(0.25)
    await bridge.on_tick()
    await fake.wait_for(lambda: fake.characters == ["LIRA", "ELIAN"])
    assert fake.violations == []
    await fake.stop()


async def test_unknown_agent_character_is_ignored(stack):
    bridge, url = stack
    fake = await connect_unreal(bridge, url)
    await bridge.on_agent_character("SKYNET")
    await asyncio.sleep(0.1)
    assert fake.characters == []
    assert fake.violations == []  # nunca llego a Unreal: no hay como violar el protocolo
    await fake.stop()


async def test_cancel_clears_playback_and_allows_next_utterance(stack):
    bridge, url = stack
    fake = await connect_unreal(bridge, url, play_speed=1.0)
    for frame in tone_frames(0.3):
        await bridge.on_frame(frame)
    await bridge.link.cancel()
    assert len(fake.cleared) == 1
    await asyncio.sleep(0.25)
    await bridge.on_tick()  # cierra el enunciado cancelado sin romper el protocolo
    await speak(bridge, 0.3)
    await fake.wait_for(lambda: len(fake.finished) == 1)
    assert fake.violations == []
    await fake.stop()


async def test_reconnect_starts_a_fresh_session(stack):
    bridge, url = stack
    first = await connect_unreal(bridge, url)
    for frame in tone_frames(0.3):
        await bridge.on_frame(frame)
    first_session = first.session
    await first.stop()
    await first.wait_for(lambda: bridge.link is None)
    second = await connect_unreal(bridge, url)
    assert second.session != first_session
    await speak(bridge, 0.3)
    await second.wait_for(lambda: len(second.finished) == 1)
    assert second.violations == []
    await second.stop()


async def test_new_connection_replaces_the_old_one(stack):
    bridge, url = stack
    old = await connect_unreal(bridge, url)
    new = await connect_unreal(bridge, url)
    await old.wait_for(lambda: old.close_code is not None)
    assert bridge.link.session == new.session
    await speak(bridge, 0.3)
    await new.wait_for(lambda: len(new.finished) == 1)
    assert new.violations == []
    await new.stop()
    await old.stop()


async def test_audio_without_unreal_is_dropped_quietly(stack):
    bridge, _ = stack
    await speak(bridge, 0.3)  # no hay nadie conectado: no debe fallar
    assert bridge.link is None


async def test_client_that_never_acks_the_handshake_is_dropped(stack, monkeypatch):
    bridge, url = stack
    monkeypatch.setattr(link_module, "HANDSHAKE_TIMEOUT", 0.2)
    async with connect(url) as ws:
        await ws.recv()  # recibe `ready` y no contesta
        with pytest.raises(ConnectionClosed):
            await asyncio.wait_for(ws.recv(), 2)
    assert bridge.link is None


async def http_get(url: str, path: str) -> tuple[int, dict[str, str], bytes]:
    host, port = url.removeprefix("ws://").split(":")
    reader, writer = await asyncio.open_connection(host, int(port))
    writer.write(
        f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
    )
    await writer.drain()
    raw = await reader.read()
    writer.close()
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode().split("\r\n")
    status = int(lines[0].split()[1])
    headers = {k.lower(): v for k, v in (line.split(": ", 1) for line in lines[1:])}
    return status, headers, body


async def test_status_reports_whether_unreal_is_connected(stack):
    bridge, url = stack
    status, headers, body = await http_get(url, "/status")
    assert status == 200
    assert headers["content-type"] == "application/json"
    assert headers["cache-control"] == "no-store"
    assert json.loads(body) == {"unreal_connected": False}

    fake = await connect_unreal(bridge, url)
    _, _, body = await http_get(url, "/status")
    assert json.loads(body) == {"unreal_connected": True}

    await fake.stop()
    await fake.wait_for(lambda: bridge.link is None)
    _, _, body = await http_get(url, "/status")
    assert json.loads(body) == {"unreal_connected": False}


async def test_other_plain_http_paths_are_not_served(stack):
    _, url = stack
    status, _, _ = await http_get(url, "/otra-cosa")
    assert status != 200


async def test_hint_wakes_the_room_follower_immediately():
    """GET /hint debe despertar a RoomFollower sin esperar al proximo poll
    (ver la razon del cambio en livekit_source.py: el poll rapido de antes
    agotaba el limite de tasa de LiveKit Cloud)."""
    bridge = Bridge(Segmenter(silence_seconds=0.15))
    follower = RoomFollower(bridge, url="wss://example.invalid", api_key="k", api_secret="s")
    server = await serve(
        make_handler(bridge),
        "127.0.0.1",
        0,
        compression=None,
        process_request=make_process_request(bridge, follower),
    )
    try:
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        assert not follower._hint_event.is_set()
        status, _, _ = await http_get(url, "/hint")
        assert status == 204
        assert follower._hint_event.is_set()
    finally:
        server.close()
        await server.wait_closed()
