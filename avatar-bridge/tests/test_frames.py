from types import SimpleNamespace

import pytest
from websockets.datastructures import Headers
from websockets.http11 import Request

from bridge import Bridge
from frames import Frames
from lease import RendererLease
from main import make_process_request


def test_stalled_capture_is_not_ready_or_replayed():
    now = [0.0]
    frames = Frames(clock=lambda: now[0])
    assert frames.snapshot() is None
    frames.push(b"\xff\xd8synthetic\xff\xd9")
    assert frames.metrics()["ready"]
    now[0] = 0.8
    assert frames.snapshot() is None
    assert not frames.metrics()["ready"]
    assert frames.metrics()["frames_received"] == 1
    with pytest.raises(ValueError):
        frames.push(b"not jpeg")


def test_raw_frames_and_capture_connection_require_internal_secret():
    frames = Frames()
    frames.push(b"\xff\xd8synthetic\xff\xd9")
    handler = make_process_request(
        Bridge(), SimpleNamespace(), RendererLease(), "s" * 32, frames
    )
    for path in ("/render/frame", "/render/health", "/capture"):
        assert handler(None, Request(path, Headers())).status_code == 403
    response = handler(
        None, Request("/render/frame", Headers({"Authorization": "Bearer " + "s" * 32}))
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    frames.clear()
    assert (
        handler(
            None,
            Request("/render/frame", Headers({"Authorization": "Bearer " + "s" * 32})),
        ).status_code
        == 503
    )
