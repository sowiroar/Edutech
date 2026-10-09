"""Reenvio de atributos del participante agente hacia el `Bridge`.

No levanta una `rtc.Room` real (eso lo cubre test_bridge_e2e.py con un
Unreal simulado completo): `RoomFollower._forward_state`/`_forward_character`
y `_on_attributes_changed` solo leen `.kind` y `.attributes.get(...)` del
participante, asi que un doble minimo (duck typing) basta para probarlos en
aislamiento.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bridge import Bridge
from livekit_source import AGENT, STANDARD, RoomFollower
from segmenter import Segmenter


@dataclass
class FakeParticipant:
    kind: object
    attributes: dict[str, str] = field(default_factory=dict)


@pytest.fixture
def follower():
    bridge = Bridge(Segmenter())
    return RoomFollower(bridge, url="wss://example.invalid", api_key="k", api_secret="s")


async def test_forward_character_reads_the_avatar_character_attribute(follower):
    calls = []
    follower._bridge.on_agent_character = lambda name: calls.append(name) or _noop()
    participant = FakeParticipant(kind=AGENT, attributes={"avatar.character": "LIRA"})
    follower._forward_character(participant)
    await _drain(follower)
    assert calls == ["LIRA"]


async def test_forward_character_does_nothing_without_the_attribute(follower):
    participant = FakeParticipant(kind=AGENT, attributes={})
    follower._forward_character(participant)  # no debe lanzar ni crear tareas
    assert follower._tasks == set()


async def test_on_attributes_changed_dispatches_state_and_character_independently(
    follower,
):
    seen_states = []
    seen_characters = []
    follower._bridge.on_agent_state = lambda s: seen_states.append(s) or _noop()
    follower._bridge.on_agent_character = lambda n: seen_characters.append(n) or _noop()
    participant = FakeParticipant(
        kind=AGENT,
        attributes={"lk.agent.state": "thinking", "avatar.character": "NEXO"},
    )

    follower._on_attributes_changed({"lk.agent.state": "thinking"}, participant)
    await _drain(follower)
    assert seen_states == ["thinking"]
    assert seen_characters == []  # no cambio: no estaba en `changed`

    follower._on_attributes_changed({"avatar.character": "NEXO"}, participant)
    await _drain(follower)
    assert seen_characters == ["NEXO"]


async def test_on_attributes_changed_ignores_non_agent_participants(follower):
    participant = FakeParticipant(
        kind=STANDARD, attributes={"avatar.character": "LIRA"}
    )
    follower._on_attributes_changed({"avatar.character": "LIRA"}, participant)
    assert follower._tasks == set()


def _noop():
    async def _coro():
        return None

    return _coro()


async def _drain(follower: RoomFollower) -> None:
    for task in list(follower._tasks):
        await task
