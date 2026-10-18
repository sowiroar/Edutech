import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from viva_metrics.app import app
from viva_metrics.contract import Event
from viva_metrics.store import ContextMismatch, MissingStart, Store

DSN = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN, reason="TEST_DATABASE_URL must point to a disposable database"
)


def event(context=None, kind="session_started", payload=None):
    ctx = context or dict(
        app_session_id=str(uuid4()),
        conversation_id=str(uuid4()),
        anonymous_id=str(uuid4()),
        environment="test",
        room_name="test-room",
        participant_identity="test-visitor",
    )
    return Event(
        **ctx,
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        source="agent",
        type=kind,
        payload=payload or {},
    )


def context(e):
    from viva_metrics.contract import SessionContext

    return {k: v for k, v in e.model_dump(mode="json").items() if k in SessionContext.model_fields}


@pytest_asyncio.fixture
async def store():
    assert DSN.rsplit("/", 1)[-1] == "test", "Refusing to reset a non-test database"
    s = Store(DSN)
    await s.connect()
    async with s.pool.acquire() as conn:
        await conn.execute("TRUNCATE usage_ledger,telemetry_events,telemetry_sessions CASCADE")
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_start_required_dedup_context_and_cost(store):
    first = event()
    usage = event(
        context(first),
        "usage_recorded",
        dict(
            provider="google",
            model="gemini-3.8-live",
            purpose="conversation",
            accounting_source="provider",
            coverage_reason="complete",
            entries=[
                dict(unit="tokens", direction="input", modality="text", cached=False, quantity=1250)
            ],
        ),
    )
    with pytest.raises(MissingStart):
        await store.ingest([usage])
    assert await store.ingest([first, usage]) == 2
    assert await store.ingest([first, usage]) == 0
    forged = event(
        dict(context(first), anonymous_id=str(uuid4())),
        "error",
        dict(component="agent", code="Test"),
    )
    with pytest.raises(ContextMismatch):
        await store.ingest([forged])
    now = datetime.now(timezone.utc)
    m = await store.metrics(now - timedelta(days=1), now + timedelta(days=1), "test", None)
    assert m["known_cost_usd"] == 0.0009375
    assert m["summary"]["sessions"] == 1
    assert (await store.metrics(now - timedelta(days=1), now + timedelta(days=1), "local", None))[
        "summary"
    ]["sessions"] == 0
    unknown = event(context(first), "usage_recorded", dict(usage.payload, model="unknown"))
    await store.ingest([unknown])
    m = await store.metrics(now - timedelta(days=1), now + timedelta(days=1), "test", None)
    assert m["known_cost_usd"] == 0.0009375
    assert next(r for r in m["usage"] if r["model"] == "unknown")["known_cost_usd"] is None


@pytest.mark.asyncio
async def test_expired_closure_and_pagination(store):
    first = event()
    await store.ingest([first])
    async with store.pool.acquire() as conn:
        await conn.execute("UPDATE telemetry_sessions SET last_seen_at=now()-interval '11 minutes'")
    await store.expire()
    now = datetime.now(timezone.utc)
    page = await store.sessions(now - timedelta(days=1), now + timedelta(days=1), "test", None)
    assert page["items"][0]["end_reason"] == "expired"
    assert len((await store.events(str(first.app_session_id)))["items"]) == 2


@pytest.mark.asyncio
async def test_private_api_signature_and_media_access(store, monkeypatch):
    monkeypatch.setenv("TELEMETRY_INTERNAL_KEY", "i" * 48)
    monkeypatch.setenv("TELEMETRY_SIGNING_SECRET", "s" * 48)
    app.state.store = store
    app.state.ready = True
    app.state.accepted = 0
    app.state.write_failed = 0
    first = event()
    ctx = context(first)
    token = jwt.encode(
        {
            "context": ctx,
            "aud": "viva-telemetry",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "s" * 48,
        algorithm="HS256",
    )
    packet = dict(context_token=token, events=[first.model_dump(mode="json")])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/metrics")).status_code == 401
        headers = {"Authorization": "Bearer " + "i" * 48}
        assert (
            await client.post("/ingest", headers=headers, json=dict(packet, media_only=True))
        ).status_code == 422
        assert (await client.post("/ingest", headers=headers, json=packet)).status_code == 200
        forged = dict(first.model_dump(mode="json"), anonymous_id=str(uuid4()))
        response = await client.post("/ingest", headers=headers, json=dict(packet, events=[forged]))
        assert response.status_code == 422
        assert token not in response.text
        app.state.ready = False
        assert (await client.post("/ingest", headers=headers, json=packet)).status_code == 503
        assert (await client.get("/health", headers=headers)).json()["ready"] is False
        assert (await client.get("/metrics?environment=other", headers=headers)).status_code == 422


@pytest.mark.asyncio
async def test_latency_denominator_is_event_boundary_not_session_count(store):
    first = event()
    ctx = context(first)
    await store.ingest(
        [
            first,
            event(ctx, "response_started", {"server_response_start_ms": 120}),
            event(ctx, "response_started", {}),
        ]
    )
    attempt_a, attempt_b = uuid4(), uuid4()
    media = []
    for kind, attempt, payload in [
        ("media_connect_started", attempt_a, {}),
        ("media_connect_started", attempt_b, {}),
        ("audio_playback_started", attempt_a, {"elapsed_ms": 300}),
    ]:
        media.append(
            Event(
                **ctx,
                event_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                source="browser",
                connection_attempt_id=attempt,
                type=kind,
                payload=payload,
            )
        )
    await store.ingest(media)
    now = datetime.now(timezone.utc)
    result = await store.metrics(now - timedelta(hours=1), now + timedelta(hours=1), "test", None)
    server = next(x for x in result["latencies"] if x["metric"] == "server_response_start_ms")
    browser = next(x for x in result["latencies"] if x["metric"] == "browser_first_audio_ms")
    assert (server["n"], server["eligible"], server["p50"]) == (1, 2, 120)
    assert (browser["n"], browser["eligible"], browser["p95"]) == (1, 2, 300)
