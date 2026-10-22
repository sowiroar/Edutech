import asyncio
from types import SimpleNamespace

import aiohttp
import pytest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import InvalidStatus

from bridge import Bridge
from frames import Frames
from lease import RendererLease
from main import make_handler, make_process_request


async def test_capture_transport_is_private_and_disconnect_removes_last_frame():
    bridge, frames, leases = Bridge(), Frames(), RendererLease()
    secret = "synthetic-test-secret-" * 2
    follower = SimpleNamespace()
    async with serve(
        make_handler(bridge, frames),
        "127.0.0.1",
        0,
        process_request=make_process_request(bridge, follower, leases, secret, frames),
    ) as server:
        port = server.sockets[0].getsockname()[1]
        async with aiohttp.ClientSession() as http:
            url = f"http://127.0.0.1:{port}/render/frame"
            async with http.get(url) as response:
                assert response.status == 403
            with pytest.raises(InvalidStatus):
                async with connect(f"ws://127.0.0.1:{port}/capture"):
                    pass
            auth = {"Authorization": "Bearer " + secret}
            async with connect(
                f"ws://127.0.0.1:{port}/capture", additional_headers=auth
            ) as capture:
                jpeg = b"\xff\xd8synthetic-only\xff\xd9"
                await capture.send(jpeg)
                for _ in range(100):
                    if frames.count:
                        break
                    await asyncio.sleep(0.01)
                async with http.get(url, headers=auth) as response:
                    assert response.status == 200
                    assert await response.read() == jpeg
                assert (
                    bridge.link is None
                )  # Capture must never claim the Unreal audio connection.
            for _ in range(100):
                if frames.source is None:
                    break
                await asyncio.sleep(0.01)
            async with http.get(url, headers=auth) as response:
                assert response.status == 503
