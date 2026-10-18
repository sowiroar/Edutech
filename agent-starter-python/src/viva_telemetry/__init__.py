"""Bounded best-effort telemetry. No transcripts, audio, tool arguments or secrets."""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import copy
import functools
import json
import logging
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import aiohttp
import jwt

logger = logging.getLogger("viva-telemetry")
current = contextvars.ContextVar("viva_telemetry", default=None)


def memory_identity(session):
    if session is None:
        return f"visitor-{uuid4()}"
    identity = getattr(session, "_viva_memory_identity", None)
    if identity is None:
        identity = f"visitor-{uuid4()}"
        session._viva_memory_identity = identity
    return identity


class UsageDelta:
    """SDK 1.8.2 session_usage_updated is cumulative per provider/model."""

    def __init__(self):
        self.previous = {}
        self.sequence = 0

    def update(self, row):
        provider = row.get("provider", "unknown")
        # LiveKit Google plugin 1.8.2 reports the provider label as "Gemini".
        if provider.lower() in ("gemini", "google"):
            provider = "google"
        key = (provider, row.get("model", "unknown"))
        counts = {
            k: max(0, int(v or 0)) for k, v in row.items() if k.endswith("_tokens")
        }
        old = self.previous.get(key, {})
        if counts == old:
            return None
        reset = any(counts.get(k, 0) < v for k, v in old.items())
        delta = {k: v - (0 if reset else old.get(k, 0)) for k, v in counts.items()}
        self.previous[key] = counts
        self.sequence += 1
        entries = []
        reason = "complete"
        for direction in ("input", "output"):
            total = delta.get(f"{direction}_tokens", 0)
            split = {
                m: delta.get(f"{direction}_{m}_tokens", 0)
                for m in ("text", "audio", "image")
            }
            if sum(split.values()) > total:
                # Do not guess the provider's accounting when details conflict.
                split = {"text": 0, "audio": 0, "image": 0}
                reason = "inconsistent"
            split["unspecified"] = total - sum(split.values())
            cached_total = (
                delta.get("input_cached_tokens", 0) if direction == "input" else 0
            )
            cached = {
                m: delta.get(f"input_cached_{m}_tokens", 0)
                if direction == "input"
                else 0
                for m in split
            }
            cached["unspecified"] = max(0, cached_total - sum(cached.values()))
            for modality, quantity in split.items():
                cache = min(quantity, cached[modality])
                if cached[modality] > quantity:
                    reason = "inconsistent"
                if quantity and modality == "unspecified" and reason == "complete":
                    reason = "modality_unknown"
                for is_cached, amount in ((False, quantity - cache), (True, cache)):
                    if amount:
                        entries.append(
                            {
                                "unit": "tokens",
                                "direction": direction,
                                "modality": modality,
                                "cached": is_cached,
                                "quantity": amount,
                            }
                        )
        return {
            "provider": key[0],
            "model": key[1],
            "purpose": "conversation",
            "entries": entries,
            "accounting_source": "provider",
            "coverage_reason": reason,
            "counter_reset": reset,
            "snapshot_sequence": self.sequence,
        }


class Emitter:
    def __init__(self, context, token, capacity=512):
        self.context = context
        self.token = token
        self.queue = asyncio.Queue(maxsize=capacity)
        self.stats = {"enqueued": 0, "persisted": 0, "dropped": 0, "write_failed": 0}
        self.started = time.monotonic()
        self.loop = asyncio.get_running_loop()
        self.agent_id = None
        self.avatar_id = None
        self.closed = False
        self.task = None
        self.start_event = None
        self.start_persisted = False
        self.inflight = 0

    def emit(self, kind, payload, **correlation):
        if self.closed:
            return
        event = dict(
            self.context,
            schema_version=1,
            event_id=str(uuid4()),
            occurred_at=datetime.now(timezone.utc).isoformat(),
            source="agent",
            agent_id=self.agent_id,
            avatar_id=self.avatar_id,
            type=kind,
            payload=copy.deepcopy(payload),
        )
        event.update(correlation)
        if kind == "session_started":
            self.start_event = event
        try:
            self.queue.put_nowait((time.monotonic(), event))
            self.stats["enqueued"] += 1
        except asyncio.QueueFull:
            self.stats["dropped"] += 1

    def thread_emit(self, kind, payload, **correlation):
        # ContextVars propagate into asyncio.to_thread; queue mutation stays on its loop.
        if not self.closed and not self.loop.is_closed():
            with contextlib.suppress(RuntimeError):
                self.loop.call_soon_threadsafe(
                    functools.partial(self.emit, kind, payload, **correlation)
                )

    def health(self):
        oldest = self.queue._queue[0][0] if self.queue.qsize() else time.monotonic()
        return dict(
            self.stats,
            queue_depth=self.queue.qsize(),
            queue_age_ms=min(86400000, max(0, (time.monotonic() - oldest) * 1000)),
        )

    async def send(self, batch):
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as client,
            client.post(
                os.environ["TELEMETRY_URL"].rstrip("/") + "/ingest",
                headers={
                    "Authorization": "Bearer " + os.environ["TELEMETRY_INTERNAL_KEY"]
                },
                json={"context_token": self.token, "events": batch},
            ) as response,
        ):
            if response.status != 200:
                raise RuntimeError("Collector unavailable")
            result = await response.json()
            if result.get("accepted") != len(batch):
                raise RuntimeError("Incomplete acknowledgment")

    async def run(self):
        last_health = time.monotonic()
        while True:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=15)
            except asyncio.TimeoutError:
                self.emit("producer_health", self.health())
                continue
            batch = [item]
            while len(batch) < 48 and not self.queue.empty():
                batch.append(self.queue.get_nowait())
            self.inflight = len(batch)
            events = [e for _, e in batch]
            if (
                not self.start_persisted
                and self.start_event
                and self.start_event not in events
            ):
                events.insert(0, self.start_event)
            success = False
            for attempt in range(3):
                try:
                    await self.send(events)
                    self.start_persisted = True
                    self.stats["persisted"] += len(batch)
                    success = True
                    break
                except Exception:
                    self.stats["write_failed"] += 1
                    logger.warning("Telemetry unavailable; counters=%s", self.health())
                    await asyncio.sleep(0.25 * (attempt + 1))
            if not success:
                self.stats["dropped"] += len(batch)
            for _ in batch:
                self.queue.task_done()
            self.inflight = 0
            if time.monotonic() - last_health > 15:
                logger.info("Telemetry counters=%s", self.health())
                self.emit("producer_health", self.health())
                last_health = time.monotonic()

    async def close(self, reason="shutdown"):
        if self.closed:
            return
        self.emit("producer_health", self.health())
        self.emit(
            "session_ended",
            {
                "reason": reason,
                "elapsed_ms": min(86400000, (time.monotonic() - self.started) * 1000),
            },
        )
        try:
            await asyncio.wait_for(self.queue.join(), timeout=3)
        except asyncio.TimeoutError:
            # Removed-from-queue events are still unacknowledged while HTTP is pending.
            self.stats["dropped"] += self.queue.qsize() + self.inflight
        self.closed = True
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        logger.info("Telemetry final counters=%s", self.health())


def install(session, ctx, model):
    """Invalid/missing telemetry configuration never prevents a voice session."""
    if not os.getenv("TELEMETRY_URL"):
        return None
    try:
        metadata = json.loads(ctx.job.metadata or "{}")
        token = metadata["telemetry_context"]
        claims = jwt.decode(
            token,
            os.environ["TELEMETRY_SIGNING_SECRET"],
            algorithms=["HS256"],
            audience="viva-telemetry",
            options={"require": ["exp", "iat", "context"]},
        )
        context = claims["context"]
        if context["room_name"] != ctx.room.name:
            raise ValueError("Room mismatch")
    except Exception:
        logger.warning("Telemetry disabled: missing or invalid signed session context")
        return None
    emitter = Emitter(context, token)
    current.set(emitter)
    session._viva_emitter = emitter
    session._viva_memory_identity = "visitor-" + context["anonymous_id"]
    emitter.emit("session_started", {"model": model})
    emitter.task = asyncio.create_task(emitter.run())
    deltas = UsageDelta()

    def usage(event):
        try:
            for row in event.usage.model_usage:
                if row.type == "llm_usage":
                    payload = deltas.update(row.model_dump())
                    if payload:
                        # Session snapshots may arrive after a handoff. The SDK does
                        # not identify which role/turn generated this increment.
                        emitter.emit(
                            "usage_recorded", payload, agent_id=None, avatar_id=None
                        )
        except Exception:
            emitter.emit(
                "error",
                {
                    "component": "telemetry",
                    "code": "UsageAdapterError",
                    "retryable": False,
                },
            )

    session.on("session_usage_updated", usage)

    thinking = [None]

    def state_changed(event):
        if event.new_state == "thinking":
            thinking[0] = time.monotonic()

    session.on("agent_state_changed", state_changed)

    def speech(event):
        handle = event.speech_handle
        started = time.monotonic()
        agent_id = emitter.agent_id
        avatar_id = emitter.avatar_id
        emitter.emit(
            "response_started",
            {
                "source": event.source,
                "boundary": "speech_handle",
                "server_response_start_ms": None
                if thinking[0] is None
                else max(0, (started - thinking[0]) * 1000),
            },
            turn_id=handle.id,
        )

        thinking[0] = None

        def done(result):
            # Keep the originating turn and agent even if a handoff already occurred.
            event_data = {
                "source": event.source,
                "boundary": "speech_handle",
                "elapsed_ms": min(86400000, (time.monotonic() - started) * 1000),
            }
            prior = (emitter.agent_id, emitter.avatar_id)
            emitter.agent_id, emitter.avatar_id = agent_id, avatar_id
            emitter.emit(
                "response_interrupted" if result.interrupted else "response_completed",
                event_data,
                turn_id=handle.id,
            )
            emitter.agent_id, emitter.avatar_id = prior

        handle.add_done_callback(done)

    session.on("speech_created", speech)

    def error(event):
        emitter.emit(
            "error",
            {
                "component": "agent",
                "code": type(event.error).__name__,
                "retryable": False,
            },
        )

    session.on("error", error)

    async def shutdown():
        await emitter.close("shutdown")

    ctx.add_shutdown_callback(shutdown)
    return emitter


def agent_changed(session, agent_id, avatar_id):
    emitter = getattr(session, "_viva_emitter", None)
    if emitter:
        previous = emitter.agent_id
        emitter.agent_id, emitter.avatar_id = agent_id, avatar_id
        emitter.emit(
            "agent_changed", {"previous_agent_id": previous, "agent_id": agent_id}
        )


def observed(purpose=None):
    """Measure owned async tools/operations without changing values or exceptions."""

    def decorate(fn):
        @functools.wraps(fn)
        async def wrapped(*args, **kwargs):
            emitter = current.get()
            if emitter is None:
                return await fn(*args, **kwargs)
            context = next((x for x in args if hasattr(type(x), "function_call")), None)
            call_id = None
            if context is not None:
                with contextlib.suppress(Exception):
                    call_id = context.function_call.call_id
            correlation = {"agent_id": emitter.agent_id, "avatar_id": emitter.avatar_id}
            if call_id:
                correlation["tool_call_id"] = call_id
            if context is not None:
                with contextlib.suppress(Exception):
                    correlation["turn_id"] = context.speech_handle.id
            payload = {"name": fn.__name__, "status": "started"}
            prefix = "tool" if purpose is None else "operation"
            if purpose:
                payload.update(purpose=purpose, usage_observed=False)
            emitter.emit(prefix + "_started", payload, **correlation)
            from .google_usage import operation

            scope = {"calls": 0, "missing": 0}
            scope_token = operation.set(scope) if purpose else None
            start = time.monotonic()
            status = "ok"
            try:
                return await fn(*args, **kwargs)
            except asyncio.CancelledError:
                status = "cancelled"
                raise
            except Exception:
                status = "error"
                raise
            finally:
                if purpose:
                    payload["usage_observed"] = (
                        purpose != "memory"
                        and scope["calls"] > 0
                        and scope["missing"] == 0
                    )
                    operation.reset(scope_token)
                emitter.emit(
                    prefix + "_completed",
                    dict(
                        payload,
                        status=status,
                        elapsed_ms=min(86400000, (time.monotonic() - start) * 1000),
                    ),
                    **correlation,
                )

        return wrapped

    return decorate
