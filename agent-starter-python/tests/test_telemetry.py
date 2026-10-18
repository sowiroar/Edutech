import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from viva_telemetry import Emitter, UsageDelta, memory_identity


def test_visitors_and_handoff_share_only_their_session():
    a, b = SimpleNamespace(), SimpleNamespace()
    assert memory_identity(a) == memory_identity(a)
    assert memory_identity(a) != memory_identity(b)
    assert "estudiante_uam" not in memory_identity(a)


def test_snapshots_not_double_counted_and_reset():
    delta = UsageDelta()
    row = {
        "provider": "google",
        "model": "gemini-3.8-live",
        "input_tokens": 100,
        "input_text_tokens": 20,
        "input_audio_tokens": 80,
        "output_tokens": 50,
        "output_audio_tokens": 50,
    }
    first = delta.update(row)
    assert sum(e["quantity"] for e in first["entries"]) == 150
    assert delta.update(row) is None
    second = delta.update(dict(row, output_tokens=70, output_audio_tokens=70))
    assert sum(e["quantity"] for e in second["entries"]) == 20
    reset = delta.update(
        dict(
            row,
            input_tokens=10,
            input_text_tokens=10,
            input_audio_tokens=0,
            output_tokens=0,
            output_audio_tokens=0,
        )
    )
    assert reset["counter_reset"]
    assert sum(e["quantity"] for e in reset["entries"]) == 10


def test_unsplit_and_cache_are_not_billed_twice():
    usage = UsageDelta().update(
        {
            "provider": "p",
            "model": "m",
            "input_tokens": 100,
            "input_cached_tokens": 20,
            "output_tokens": 40,
        }
    )
    assert sum(e["quantity"] for e in usage["entries"]) == 140
    assert usage["coverage_reason"] == "modality_unknown"
    assert sum(e["quantity"] for e in usage["entries"] if e["cached"]) == 20


@pytest.mark.asyncio
async def test_queue_bounded_and_failing_transport_does_not_block_producer():
    emitter = Emitter({"app_session_id": str(uuid4())}, "token", capacity=2)
    emitter.emit("session_started", {})
    for _ in range(50):
        emitter.emit(
            "error", {"component": "agent", "code": "Test", "retryable": False}
        )
    assert emitter.queue.qsize() == 2
    assert emitter.stats["dropped"] == 49

    async def fail(batch):
        raise ConnectionError("PRIVATE")

    emitter.send = fail
    task = asyncio.create_task(emitter.run())
    await asyncio.sleep(0.05)
    assert emitter.stats["write_failed"] >= 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_shutdown_counts_unacknowledged_inflight_events(monkeypatch):
    emitter = Emitter({"app_session_id": str(uuid4())}, "token")
    sending = asyncio.Event()

    async def pending(batch):
        sending.set()
        await asyncio.Event().wait()

    async def drain_timeout():
        raise asyncio.TimeoutError()

    emitter.send = pending
    emitter.emit("session_started", {})
    emitter.task = asyncio.create_task(emitter.run())
    await sending.wait()
    assert emitter.queue.qsize() == 0
    assert emitter.inflight == 1
    monkeypatch.setattr(emitter.queue, "join", drain_timeout)
    await emitter.close()
    assert emitter.stats["dropped"] == emitter.stats["enqueued"] == 3
    assert emitter.stats["persisted"] == 0
    assert emitter.task.cancelled()


@pytest.mark.asyncio
async def test_provider_adapter_preserves_output_and_missing_usage():
    from viva_telemetry import current
    from viva_telemetry.google_usage import wrap_client

    response = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            model_dump=lambda: {
                "prompt_token_count": 10,
                "candidates_token_count": 4,
                "thoughts_token_count": 2,
            }
        ),
        response_id="provider-request",
    )
    raw = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **kwargs: response)
    )
    emitter = Emitter({"app_session_id": str(uuid4())}, "token")
    token = current.set(emitter)
    try:
        assert (
            wrap_client(raw, "memory").models.generate_content(
                model="gemini-2.5-flash", contents="PRIVATE"
            )
            is response
        )
        await asyncio.sleep(0)
        payload = emitter.queue.get_nowait()[1]["payload"]
        assert sum(e["quantity"] for e in payload["entries"]) == 16
        assert "PRIVATE" not in str(payload)
    finally:
        current.reset(token)


def test_installed_sdk_usage_shape_and_provider_label():
    from livekit.agents.metrics.usage import LLMModelUsage

    row = LLMModelUsage(
        provider="Gemini",
        model="gemini-3.8-live",
        input_tokens=21,
        input_text_tokens=21,
        output_tokens=17,
        output_audio_tokens=17,
    )
    payload = UsageDelta().update(row.model_dump())
    assert payload["provider"] == "google"
    assert sum(e["quantity"] for e in payload["entries"]) == 38


@pytest.mark.asyncio
async def test_late_tool_cancellation_keeps_origin_agent():
    from viva_telemetry import current, observed

    emitter = Emitter({"app_session_id": str(uuid4())}, "token")
    emitter.agent_id = "LiraAgent"
    started = asyncio.Event()

    @observed()
    async def tool():
        started.set()
        await asyncio.Event().wait()

    token = current.set(emitter)
    try:
        task = asyncio.create_task(tool())
        await started.wait()
        emitter.agent_id = "NexusAgent"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        rows = [emitter.queue.get_nowait()[1] for _ in range(2)]
        assert rows[-1]["agent_id"] == "LiraAgent"
        assert rows[-1]["payload"]["status"] == "cancelled"
    finally:
        current.reset(token)


@pytest.mark.asyncio
async def test_session_usage_does_not_invent_current_agent_attribution(monkeypatch):
    import json
    import time

    import jwt
    from livekit.agents.metrics.usage import LLMModelUsage

    from viva_telemetry import current, install

    monkeypatch.setenv("TELEMETRY_URL", "http://unused")
    monkeypatch.setenv("TELEMETRY_SIGNING_SECRET", "s" * 48)
    token = jwt.encode(
        {
            "aud": "viva-telemetry",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
            "context": {"room_name": "test", "anonymous_id": str(uuid4())},
        },
        "s" * 48,
        algorithm="HS256",
    )
    hooks = {}
    session = SimpleNamespace(on=lambda name, callback: hooks.update({name: callback}))
    ctx = SimpleNamespace(
        job=SimpleNamespace(metadata=json.dumps({"telemetry_context": token})),
        room=SimpleNamespace(name="test"),
        add_shutdown_callback=lambda callback: None,
    )
    scope = current.set(None)
    emitter = install(session, ctx, "gemini-3.8-live")
    try:
        emitter.agent_id = "NexusAgent"
        row = LLMModelUsage(
            provider="Gemini",
            model="gemini-3.8-live",
            input_tokens=2,
            input_text_tokens=2,
        )
        hooks["session_usage_updated"](
            SimpleNamespace(usage=SimpleNamespace(model_usage=[row]))
        )
        emitter.queue.get_nowait()  # start
        usage = emitter.queue.get_nowait()[1]
        assert usage["type"] == "usage_recorded"
        assert usage["agent_id"] is None
        assert usage["avatar_id"] is None
        assert usage["payload"]["entries"][0]["quantity"] == 2
    finally:
        emitter.task.cancel()
        await asyncio.gather(emitter.task, return_exceptions=True)
        current.reset(scope)
