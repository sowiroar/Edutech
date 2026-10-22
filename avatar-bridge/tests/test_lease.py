import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from websockets.datastructures import Headers
from websockets.http11 import Request

from bridge import Bridge
from lease import RendererLease
from livekit_source import AGENT, RoomFollower
from main import make_process_request


def test_exclusive_release_expiry_and_stale_token():
    now = [0.0]
    leases = RendererLease(clock=lambda: now[0])
    a = leases.acquire("viva_a")
    assert a and leases.acquire("viva_b") is None
    assert not leases.release("viva_a", "wrong")
    now[0] = 29
    assert leases.renew(a.room, a.token)
    now[0] = 60
    b = leases.acquire("viva_b")
    assert b and not leases.renew(a.room, a.token)
    assert not leases.release(a.room, a.token)
    assert leases.matches(b.room, b.token)


async def test_old_room_events_queued_before_release_are_discarded():
    leases = RendererLease()
    a = leases.acquire("viva_a")
    bridge = Bridge()
    bridge.on_agent_state = AsyncMock()
    follower = RoomFollower(bridge, "ws://invalid", "k", "s", leases=leases)
    follower._binding = (a.room, a.token)
    follower._forward_state(
        SimpleNamespace(kind=AGENT, attributes={"lk.agent.state": "thinking"})
    )
    leases.release(a.room, a.token)
    leases.acquire("viva_b")
    await asyncio.gather(*list(follower._tasks))
    bridge.on_agent_state.assert_not_awaited()


async def test_managed_follower_does_not_search_any_unleased_room():
    follower = RoomFollower(Bridge(), "ws://invalid", "k", "s", leases=RendererLease())
    api = SimpleNamespace(room=SimpleNamespace(list_rooms=AsyncMock()))
    assert await follower._find_room(api) is None
    api.room.list_rooms.assert_not_awaited()


def test_http_reservation_requires_server_secret_and_rejects_second_owner():
    leases = RendererLease()
    bridge = Bridge()
    bridge.link = object()
    follower = SimpleNamespace(hint=lambda: None, ready_for=lambda *_: False)
    handler = make_process_request(bridge, follower, leases, "s" * 32)

    def call(room, secret):
        return handler(
            None,
            Request(
                "/lease/acquire",
                Headers(
                    {
                        "Authorization": "Bearer " + secret,
                        "X-Avatar-Room": room,
                    }
                ),
            ),
        )

    assert call("viva_a", "wrong").status_code == 403
    assert call("viva_a", "s" * 32).status_code == 200
    assert call("viva_b", "s" * 32).status_code == 409
