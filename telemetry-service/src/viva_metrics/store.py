import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg

from .contract import Event, SessionContext
from .pricing import price, rates
from .privacy import redact


class MissingStart(ValueError):
    pass


class ContextMismatch(ValueError):
    pass


class Store:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5, command_timeout=5)
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(683192)")
            await conn.execute(
                (Path(__file__).parents[2] / "migrations/001_telemetry.sql").read_text()
            )
            for rate in rates():
                await conn.execute(
                    """INSERT INTO pricing_rates VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    ON CONFLICT DO NOTHING""",
                    rate["id"],
                    rate["provider"],
                    rate["model"],
                    rate["unit"],
                    rate["direction"],
                    rate["modality"],
                    rate["cached"],
                    datetime.fromisoformat(rate["effective_at"]),
                    rate["usd_per_unit"],
                    rate["source_url"],
                )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def ingest(self, events: list[Event]):
        accepted = 0
        async with self.pool.acquire() as conn, conn.transaction():
            for event in events:
                data = event.model_dump(mode="json")
                if event.schema_version == 1:
                    data.pop("parent_span_id", None)
                data["received_at"] = datetime.now(timezone.utc).isoformat()
                context = SessionContext.model_validate(
                    {k: data[k] for k in SessionContext.model_fields}
                ).model_dump(mode="json")
                if event.type == "session_started":
                    await conn.execute(
                        """INSERT INTO telemetry_sessions(id,context,started_at)
                        VALUES($1,$2,$3) ON CONFLICT DO NOTHING""",
                        event.app_session_id,
                        json.dumps(context),
                        event.occurred_at,
                    )
                row = await conn.fetchrow(
                    "SELECT context FROM telemetry_sessions WHERE id=$1 FOR UPDATE",
                    event.app_session_id,
                )
                if row is None:
                    raise MissingStart()
                if json.loads(row["context"]) != context:
                    raise ContextMismatch()
                transcript = None
                if event.type == "conversation_message":
                    # Fail closed: server and session must both have opted in.
                    capture = await conn.fetchval(
                        "SELECT data->'payload'->>'transcript_capture' FROM telemetry_events "
                        "WHERE session_id=$1 AND type='session_started' LIMIT 1",
                        event.app_session_id,
                    )
                    if (
                        os.getenv("TELEMETRY_CAPTURE_TRANSCRIPTS", "false").lower() != "true"
                        or capture != "true"
                    ):
                        continue
                    text, truncated = redact(data["payload"].pop("text"))
                    data["payload"]["truncated"] |= truncated
                    transcript = text
                inserted = await conn.fetchval(
                    """INSERT INTO telemetry_events(event_id,session_id,occurred_at,type,source,data)
                    VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING RETURNING event_id""",
                    event.event_id,
                    event.app_session_id,
                    event.occurred_at,
                    event.type,
                    event.source,
                    json.dumps(data),
                )
                if inserted is None:
                    continue
                accepted += 1
                if transcript is not None:
                    days = max(
                        1, min(30, int(os.getenv("TELEMETRY_TRANSCRIPT_RETENTION_DAYS", "7")))
                    )
                    await conn.execute(
                        """INSERT INTO telemetry_transcripts(event_id,session_id,message_id,text,expires_at)
                        VALUES($1,$2,$3,$4,$5::timestamptz + make_interval(days => $6)) ON CONFLICT DO NOTHING""",
                        event.event_id,
                        event.app_session_id,
                        event.payload["message_id"],
                        transcript,
                        event.occurred_at,
                        days,
                    )
                await conn.execute(
                    "UPDATE telemetry_sessions SET last_seen_at=now() WHERE id=$1",
                    event.app_session_id,
                )
                if event.type == "session_ended":
                    await conn.execute(
                        """UPDATE telemetry_sessions SET ended_at=COALESCE(ended_at,$2),
                        end_reason=COALESCE(end_reason,$3) WHERE id=$1""",
                        event.app_session_id,
                        event.occurred_at,
                        event.payload["reason"],
                    )
                if event.type != "usage_recorded":
                    continue
                payload = event.payload
                for index, entry in enumerate(payload["entries"]):
                    rate = await conn.fetchrow(
                        """SELECT id,usd_per_unit FROM pricing_rates
                        WHERE provider=$1 AND model=$2 AND unit=$3 AND direction=$4 AND modality=$5 AND cached=$6
                          AND effective_at<=$7 ORDER BY effective_at DESC LIMIT 1""",
                        payload["provider"],
                        payload["model"].removeprefix("models/"),
                        entry["unit"],
                        entry["direction"],
                        entry["modality"],
                        entry["cached"],
                        event.occurred_at,
                    )
                    # Inconsistent or derived usage is explicitly excluded from known provider costs.
                    eligible = payload["accounting_source"] == "provider" and payload[
                        "coverage_reason"
                    ] in ("complete", "modality_unknown")
                    rate = rate if eligible else None
                    cost = price(entry["quantity"], rate["usd_per_unit"] if rate else None)
                    await conn.execute(
                        """INSERT INTO usage_ledger VALUES
                        ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)""",
                        event.event_id,
                        index,
                        event.app_session_id,
                        payload["provider"],
                        payload["model"],
                        payload["purpose"],
                        event.request_id,
                        payload["attempt"],
                        entry["unit"],
                        entry["direction"],
                        entry["modality"],
                        entry["cached"],
                        entry["quantity"],
                        payload["accounting_source"],
                        rate["id"] if rate else None,
                        cost,
                        "list_estimate" if rate else "unknown",
                    )
        return accepted

    async def purge_transcripts(self):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM telemetry_transcripts WHERE expires_at<=now()")

    async def expire(self):
        # Transactional explicit collector expiration, never successful completion.
        async with self.pool.acquire() as conn, conn.transaction():
            rows = await conn.fetch("""SELECT id,context,last_seen_at FROM telemetry_sessions
                WHERE ended_at IS NULL AND last_seen_at < now()-interval '10 minutes'
                FOR UPDATE SKIP LOCKED""")
            for row in rows:
                event = Event(
                    **json.loads(row["context"]),
                    event_id=uuid4(),
                    source="collector",
                    occurred_at=datetime.now(timezone.utc),
                    type="session_ended",
                    payload={"reason": "expired"},
                )
                data = event.model_dump(mode="json")
                if event.schema_version == 1:
                    data.pop("parent_span_id", None)
                data["received_at"] = datetime.now(timezone.utc).isoformat()
                await conn.execute(
                    """INSERT INTO telemetry_events(event_id,session_id,occurred_at,type,source,data)
                    VALUES($1,$2,$3,$4,$5,$6)""",
                    event.event_id,
                    row["id"],
                    event.occurred_at,
                    event.type,
                    event.source,
                    json.dumps(data),
                )
                await conn.execute(
                    "UPDATE telemetry_sessions SET ended_at=$2,end_reason='expired' WHERE id=$1",
                    row["id"],
                    event.occurred_at,
                )

    async def metrics(self, start, end, environment, mode):
        async with (
            self.pool.acquire() as conn,
            conn.transaction(isolation="repeatable_read", readonly=True),
        ):
            params = (start, end, environment, mode)
            scope = "s.started_at >= $1 AND s.started_at < $2 AND s.context->>'environment'=$3 AND ($4::text IS NULL OR s.context->>'presentation_mode'=$4)"
            summary = dict(
                await conn.fetchrow(
                    f"""SELECT count(*) sessions,
                count(*) FILTER(WHERE ended_at IS NULL) active,
                count(*) FILTER(WHERE end_reason='expired') expired,
                count(DISTINCT context->>'anonymous_id') visitors,
                count(*) FILTER(WHERE ended_at IS NOT NULL AND end_reason<>'expired') duration_samples,
                avg(extract(epoch FROM ended_at-started_at)*1000) FILTER(WHERE ended_at IS NOT NULL AND end_reason<>'expired')::float8 mean_duration_ms
                FROM telemetry_sessions s WHERE {scope}""",
                    *params,
                )
            )
            usage = await conn.fetch(
                f"""SELECT provider,model,purpose,unit,direction,modality,cached,
                sum(quantity)::float8 quantity,sum(cost_usd)::float8 known_cost_usd,
                count(*) entries,count(*) FILTER(WHERE cost_usd IS NOT NULL) priced_entries
                FROM usage_ledger l JOIN telemetry_sessions s ON s.id=l.session_id WHERE {scope}
                GROUP BY provider,model,purpose,unit,direction,modality,cached
                ORDER BY provider,model,purpose,direction,modality,cached""",
                *params,
            )
            events = await conn.fetch(
                f"""SELECT type,count(*) n FROM telemetry_events e
                JOIN telemetry_sessions s ON s.id=e.session_id WHERE {scope} GROUP BY type ORDER BY type""",
                *params,
            )
            latencies = []
            for kind, field, label in [
                ("response_completed", "elapsed_ms", "server_speech_handle_duration_ms"),
                ("response_started", "server_response_start_ms", "server_response_start_ms"),
            ]:
                row = await conn.fetchrow(
                    f"""SELECT count(*) FILTER(WHERE data->'payload'->>$6 IS NOT NULL) n, count(*) eligible,
                    percentile_cont(.5) WITHIN GROUP(ORDER BY (data->'payload'->>$6)::float8) p50,
                    percentile_cont(.95) WITHIN GROUP(ORDER BY (data->'payload'->>$6)::float8) p95
                    FROM telemetry_events e JOIN telemetry_sessions s ON s.id=e.session_id
                    WHERE {scope} AND type=$5""",
                    *params,
                    kind,
                    field,
                )
                values = dict(row)
                basis = "response_events"
                latencies.append(dict(metric=label, coverage_basis=basis, **values))
            # One first playback per registered (session, attempt), never numerator > denominator.
            browser = await conn.fetchrow(
                f"""WITH scoped AS (
                    SELECT e.* FROM telemetry_events e JOIN telemetry_sessions s ON s.id=e.session_id WHERE {scope}
                ), attempts AS (
                    SELECT session_id,data->>'connection_attempt_id' attempt,min(occurred_at) began
                    FROM scoped WHERE type='media_connect_started' AND data->>'connection_attempt_id' IS NOT NULL
                    GROUP BY session_id,data->>'connection_attempt_id'
                ), paired AS (
                    SELECT a.*,p.ms FROM attempts a LEFT JOIN LATERAL (
                        SELECT (e.data->'payload'->>'elapsed_ms')::float8 ms FROM scoped e
                        WHERE e.session_id=a.session_id AND e.data->>'connection_attempt_id'=a.attempt
                        AND e.type='audio_playback_started' AND e.occurred_at>=a.began
                        ORDER BY e.occurred_at,e.event_id LIMIT 1
                    ) p ON true
                ) SELECT count(ms) n,count(*) eligible,
                    percentile_cont(.5) WITHIN GROUP(ORDER BY ms) p50,
                    percentile_cont(.95) WITHIN GROUP(ORDER BY ms) p95,
                    (SELECT count(*) FROM scoped WHERE type='audio_playback_started') - count(ms) excluded_events
                FROM paired""",
                *params,
            )
            latencies.append(
                dict(
                    metric="browser_first_audio_ms",
                    coverage_basis="connection_attempts",
                    **dict(browser),
                )
            )
            operations = await conn.fetch(
                f"""SELECT type,data->'payload'->>'name' name,data->'payload'->>'purpose' purpose,
                count(*) calls,
                count(*) FILTER(WHERE data->'payload'->>'status'='ok') ok,
                count(*) FILTER(WHERE data->'payload'->>'status'='error') errors,
                count(*) FILTER(WHERE data->'payload'->>'status'='cancelled') cancelled,
                count(*) FILTER(WHERE data->'payload'->>'elapsed_ms' IS NOT NULL) timed,
                percentile_cont(.5) WITHIN GROUP(ORDER BY (data->'payload'->>'elapsed_ms')::float8) p50,
                percentile_cont(.95) WITHIN GROUP(ORDER BY (data->'payload'->>'elapsed_ms')::float8) p95
                FROM telemetry_events e JOIN telemetry_sessions s ON s.id=e.session_id WHERE {scope}
                AND type IN ('tool_completed','operation_completed') GROUP BY type,name,purpose ORDER BY calls DESC,name""",
                *params,
            )
            quality = dict(
                await conn.fetchrow(
                    f"""SELECT count(DISTINCT e.session_id) FILTER(WHERE type='error') sessions_with_errors,
                count(*) FILTER(WHERE type='agent_changed' AND data->'payload'->>'previous_agent_id' IS NOT NULL
                    AND data->'payload'->>'previous_agent_id'<>data->'payload'->>'agent_id') handoffs,
                count(*) FILTER(WHERE type='response_interrupted') interrupted,
                count(*) FILTER(WHERE type='usage_recorded' AND data->'payload'->>'coverage_reason'<>'complete') incomplete_usage_reports,
                count(*) FILTER(WHERE type='retrieval_completed' AND data->'payload'->>'result_available'='false') retrieval_without_result,
                count(*) FILTER(WHERE type IN ('response_interrupted','response_completed')) finished_responses
                FROM telemetry_events e JOIN telemetry_sessions s ON s.id=e.session_id WHERE {scope}""",
                    *params,
                )
            )
            producers = await conn.fetch(
                f"""SELECT DISTINCT ON (e.session_id,e.source) e.session_id,e.occurred_at,e.data->'payload' payload
                FROM telemetry_events e JOIN telemetry_sessions s ON s.id=e.session_id WHERE {scope}
                AND type='producer_health' ORDER BY e.session_id,e.source,e.occurred_at DESC,e.event_id DESC""",
                *params,
            )
            missing = await conn.fetchval(
                f"""SELECT count(*) FROM telemetry_events e
                JOIN telemetry_sessions s ON s.id=e.session_id WHERE {scope}
                AND type='operation_completed' AND data->'payload'->>'usage_observed'='false'""",
                *params,
            )
            costs = [float(r["known_cost_usd"]) for r in usage if r["known_cost_usd"] is not None]
            return dict(
                summary=summary,
                usage=[dict(r) for r in usage],
                operations=[dict(r) for r in operations],
                quality=quality,
                producers=[dict(r, payload=json.loads(r["payload"])) for r in producers],
                event_counts=[dict(r) for r in events],
                latencies=latencies,
                known_cost_usd=sum(costs) if costs else None,
                unmetered_operations=missing,
                turn_to_playback_ms=None,
                scope="Sessions started in period; their events are included even if received later",
                cost_note="Paid standard list estimate; excludes unknown usage, infrastructure, GPU, network and taxes",
            )

    async def sessions(self, start, end, environment, mode, before=None):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id,context,started_at,last_seen_at,ended_at,end_reason
                FROM telemetry_sessions WHERE started_at >= $1 AND started_at < $2
                AND context->>'environment'=$3 AND ($4::text IS NULL OR context->>'presentation_mode'=$4)
                AND ($5::uuid IS NULL OR (started_at,id)<(SELECT started_at,id FROM telemetry_sessions WHERE id=$5))
                ORDER BY started_at DESC,id DESC LIMIT 51""",
                start,
                end,
                environment,
                mode,
                UUID(before) if before else None,
            )
        return dict(
            items=[dict(r, context=json.loads(r["context"])) for r in rows[:50]],
            next_cursor=str(rows[49]["id"]) if len(rows) > 50 else None,
        )

    async def events(self, session_id, before=None, view="all"):
        if view not in ("all", "conversation", "actions"):
            raise ValueError("Invalid view")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT e.event_id,e.data,e.received_at,t.text FROM telemetry_events e
                LEFT JOIN telemetry_transcripts t ON t.event_id=e.event_id AND t.expires_at>now()
                WHERE e.session_id=$1
                AND ($3='all' OR ($3='conversation' AND e.type='conversation_message')
                     OR ($3='actions' AND e.type IN ('tool_started','tool_completed','operation_started','operation_completed','agent_changed','error','retrieval_completed')))
                AND ($2::uuid IS NULL OR (e.received_at,e.event_id)<(SELECT received_at,event_id FROM telemetry_events WHERE event_id=$2 AND session_id=$1))
                ORDER BY e.received_at DESC,e.event_id DESC LIMIT 101""",
                UUID(session_id),
                UUID(before) if before else None,
                view,
            )
            session = await conn.fetchrow(
                "SELECT id,context,started_at,ended_at,end_reason FROM telemetry_sessions WHERE id=$1",
                UUID(session_id),
            )
            capture = await conn.fetchval(
                "SELECT data->'payload'->>'transcript_capture' FROM telemetry_events WHERE session_id=$1 AND type='session_started' LIMIT 1",
                UUID(session_id),
            )
            counts = await conn.fetch(
                "SELECT type,count(*) n FROM telemetry_events WHERE session_id=$1 GROUP BY type",
                UUID(session_id),
            )
        return dict(
            session=dict(session, context=json.loads(session["context"])) if session else None,
            transcript_capture=capture == "true",
            counts=[dict(row) for row in counts],
            items=[self.present_event(r) for r in rows[:100]],
            next_cursor=str(rows[99]["event_id"]) if len(rows) > 100 else None,
        )

    @staticmethod
    def present_event(row):
        data = dict(json.loads(row["data"]), received_at=row["received_at"])
        if data["type"] == "conversation_message":
            data["payload"]["text"] = row["text"]
            data["payload"]["text_available"] = row["text"] is not None
        return data
