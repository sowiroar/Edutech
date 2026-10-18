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


@pytest.mark.asyncio
async def test_duplicate_and_orphan_playback_do_not_inflate_coverage(store):
    first = event()
    ctx = context(first)
    attempt = uuid4()

    def media(kind, attempt_id, ms=None):
        return Event(
            **ctx,
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            source="browser",
            connection_attempt_id=attempt_id,
            type=kind,
            payload={"elapsed_ms": ms},
        )

    await store.ingest(
        [
            first,
            media("media_connect_started", attempt),
            media("audio_playback_started", attempt, 100),
            media("audio_playback_started", attempt, 200),
            media("audio_playback_started", uuid4(), 300),
            media("audio_playback_started", None, 400),
        ]
    )
    now = datetime.now(timezone.utc)
    metrics = await store.metrics(now - timedelta(hours=1), now + timedelta(hours=1), "test", None)
    row = next(x for x in metrics["latencies"] if x["metric"] == "browser_first_audio_ms")
    assert (row["n"], row["eligible"], row["p95"], row["excluded_events"]) == (1, 1, 100, 3)


@pytest.mark.asyncio
async def test_transcripts_separate_expire_and_require_optin(store, monkeypatch):
    first = event()
    first.schema_version = 2
    first.payload["transcript_capture"] = True
    ctx = context(first)
    message = Event(
        **ctx,
        schema_version=2,
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        source="agent",
        type="conversation_message",
        payload={
            "message_id": "m1",
            "role": "user",
            "text": "Correo a@example.com",
            "redaction": "basic-v1",
        },
    )
    await store.ingest([first, message])
    assert len((await store.events(str(first.app_session_id)))["items"]) == 1
    monkeypatch.setenv("TELEMETRY_CAPTURE_TRANSCRIPTS", "true")
    assert await store.ingest([message]) == 1
    assert await store.ingest([message]) == 0
    rows = (await store.events(str(first.app_session_id)))["items"]
    assert rows[0]["payload"]["text"] == "Correo [CORREO]"
    async with store.pool.acquire() as conn:
        data = await conn.fetchval(
            "SELECT data::text FROM telemetry_events WHERE event_id=$1", message.event_id
        )
        assert "Correo" not in data and "a@example" not in data
        await conn.execute("UPDATE telemetry_transcripts SET expires_at=now()-interval '1 second'")
    assert (await store.events(str(first.app_session_id)))["items"][0]["payload"]["text"] is None
    await store.purge_transcripts()
    async with store.pool.acquire() as conn:
        assert await conn.fetchval("SELECT count(*) FROM telemetry_transcripts") == 0


@pytest.mark.asyncio
async def test_operations_handoffs_and_latest_health(store):
    first = event()
    ctx = context(first)
    health = dict(
        enqueued=10, persisted=7, dropped=2, write_failed=3, queue_depth=1, queue_age_ms=3
    )
    await store.ingest(
        [
            first,
            event(ctx, "tool_completed", dict(name="search", status="ok", elapsed_ms=100)),
            event(ctx, "tool_completed", dict(name="search", status="error", elapsed_ms=300)),
            event(ctx, "agent_changed", dict(agent_id="Lira")),
            event(ctx, "agent_changed", dict(previous_agent_id="Lira", agent_id="Nexus")),
            event(ctx, "producer_health", health),
            event(ctx, "producer_health", dict(health, enqueued=20)),
        ]
    )
    now = datetime.now(timezone.utc)
    m = await store.metrics(now - timedelta(hours=1), now + timedelta(hours=1), "test", None)
    assert m["operations"][0]["calls"] == 2 and m["operations"][0]["errors"] == 1
    assert m["operations"][0]["p50"] == 200
    assert m["quality"]["handoffs"] == 1
    assert len(m["producers"]) == 1 and m["producers"][0]["payload"]["enqueued"] == 20


@pytest.mark.asyncio
async def test_filtered_pagination_does_not_hide_conversation_behind_technical_events(
    store, monkeypatch
):
    monkeypatch.setenv("TELEMETRY_CAPTURE_TRANSCRIPTS", "true")
    first = event()
    first.schema_version = 2
    first.payload["transcript_capture"] = True
    ctx = context(first)
    message = Event(
        **ctx,
        schema_version=2,
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        source="agent",
        type="conversation_message",
        payload={"message_id": "m1", "role": "assistant", "text": "Hola", "redaction": "basic-v1"},
    )
    await store.ingest([first, message] + [event(ctx, "response_started", {}) for _ in range(105)])
    all_events = await store.events(str(first.app_session_id))
    assert len(all_events["items"]) == 100 and all_events["next_cursor"]
    messages = await store.events(str(first.app_session_id), view="conversation")
    assert len(messages["items"]) == 1 and messages["items"][0]["payload"]["text"] == "Hola"
    assert messages["transcript_capture"]
    earlier = await store.events(str(first.app_session_id), before=all_events["next_cursor"])
    assert len(earlier["items"]) == 7
    assert not set(x["event_id"] for x in earlier["items"]) & set(
        x["event_id"] for x in all_events["items"]
    )


@pytest.mark.asyncio
async def test_v1_stored_envelope_stays_valid_for_legacy_readers(store):
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    first = event()
    await store.ingest([first])
    async with store.pool.acquire() as conn:
        data = json.loads(
            await conn.fetchval(
                "SELECT data FROM telemetry_events WHERE event_id=$1", first.event_id
            )
        )
    schema = json.loads(
        (Path(__file__).parents[2] / "contracts/telemetry-event.v1.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(data)
