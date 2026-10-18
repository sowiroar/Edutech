"""Private collector: never publish its port on an untrusted network."""

import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .contract import MEDIA_TYPES, Event, SessionContext
from .store import ContextMismatch, MissingStart, Store


@asynccontextmanager
async def lifespan(app):
    if (
        len(os.environ.get("TELEMETRY_INTERNAL_KEY", "")) < 32
        or len(os.environ.get("TELEMETRY_SIGNING_SECRET", "")) < 32
    ):
        raise RuntimeError("Telemetry secrets must be configured (at least 32 characters)")
    app.state.store = Store(os.environ["DATABASE_URL"])
    app.state.ready = False
    app.state.accepted = 0
    app.state.write_failed = 0

    async def maintain():
        while True:
            try:
                if app.state.store.pool is None:
                    await app.state.store.connect()
                await app.state.store.expire()
                app.state.ready = True
            except Exception:
                if app.state.store.pool is not None:
                    app.state.store.pool.terminate()
                    app.state.store.pool = None
                app.state.ready = False
                app.state.write_failed += 1
            await asyncio.sleep(15)

    task = asyncio.create_task(maintain())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    await app.state.store.close()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # FastAPI's default error embeds rejected input. Never reflect payloads or secrets.
    return JSONResponse({"error": "Invalid telemetry request"}, status_code=422)


async def authorized(request: Request):
    expected = os.environ.get("TELEMETRY_INTERNAL_KEY", "")
    supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
    if len(expected) < 32 or not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Unauthorized")


@app.get("/health", dependencies=[Depends(authorized)])
async def health():
    return dict(
        ready=app.state.ready, accepted=app.state.accepted, write_failed=app.state.write_failed
    )


async def bounded_body(request):
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 262144:
            raise HTTPException(413, "Batch too large")
    try:
        body = json.loads(data)
        if not isinstance(body, dict):
            raise ValueError()
        return body
    except ValueError:
        raise HTTPException(422, "Invalid JSON") from None


def signed_context(token):
    try:
        claims = jwt.decode(
            token,
            os.environ["TELEMETRY_SIGNING_SECRET"],
            algorithms=["HS256"],
            audience="viva-telemetry",
            options={"require": ["exp", "iat", "context"]},
        )
        return SessionContext.model_validate(claims["context"]).model_dump(mode="json")
    except (jwt.PyJWTError, ValidationError, KeyError, TypeError):
        raise HTTPException(401, "Invalid session context") from None


@app.post("/ingest", dependencies=[Depends(authorized)])
async def ingest(request: Request):
    body = await bounded_body(request)
    context = signed_context(body.get("context_token", ""))
    raw = body.get("events")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise HTTPException(422, "Expected 1 to 50 events")
    try:
        events = [Event.model_validate(e) for e in raw]
        for event in events:
            if event.source == "collector":
                raise ValueError()
            data = event.model_dump(mode="json")
            if any(data[k] != value for k, value in context.items()):
                raise ValueError()
            if abs((event.occurred_at - datetime.now(timezone.utc)).total_seconds()) > 86400:
                raise ValueError()
        # Browser API sets this marker, never accepts agent lifecycle/usage there.
        if body.get("media_only") and any(
            e.source != "browser" or e.type not in MEDIA_TYPES for e in events
        ):
            raise ValueError()
    except (ValidationError, ValueError, TypeError):
        raise HTTPException(422, "Invalid event or session binding") from None
    if not app.state.ready:
        raise HTTPException(503, "Telemetry storage unavailable")
    try:
        inserted = await app.state.store.ingest(events)
        app.state.accepted += inserted
        return dict(accepted=len(events), inserted=inserted)
    except MissingStart:
        raise HTTPException(409, "Session start required") from None
    except ContextMismatch:
        raise HTTPException(409, "Context mismatch") from None
    except Exception:
        app.state.write_failed += 1
        raise HTTPException(503, "Telemetry storage unavailable") from None


def period(request):
    try:
        now = datetime.now(timezone.utc)
        start = datetime.fromisoformat(
            request.query_params.get("from", (now - timedelta(days=1)).isoformat()).replace(
                "Z", "+00:00"
            )
        )
        end = datetime.fromisoformat(
            request.query_params.get("to", now.isoformat()).replace("Z", "+00:00")
        )
        environment = request.query_params.get("environment", "local")
        mode = request.query_params.get("mode") or None
        if (
            start.tzinfo is None
            or end.tzinfo is None
            or not timedelta(0) < end - start <= timedelta(days=90)
        ):
            raise ValueError()
        if environment not in ("local", "test", "uam-demo", "production") or mode not in (
            None,
            "voice",
            "avatar",
        ):
            raise ValueError()
        return start, end, environment, mode
    except ValueError:
        raise HTTPException(
            422, "Invalid time range (maximum 90 days), environment or mode"
        ) from None


async def query(method, *args):
    if not app.state.ready:
        raise HTTPException(503, "Telemetry storage unavailable")
    try:
        return await method(*args)
    except ValueError:
        raise HTTPException(422, "Invalid cursor or identifier") from None
    except Exception:
        app.state.write_failed += 1
        raise HTTPException(503, "Telemetry storage unavailable") from None


@app.get("/metrics", dependencies=[Depends(authorized)])
async def metrics(request: Request):
    return await query(app.state.store.metrics, *period(request))


@app.get("/sessions", dependencies=[Depends(authorized)])
async def sessions(request: Request):
    return await query(
        app.state.store.sessions, *period(request), request.query_params.get("cursor")
    )


@app.get("/sessions/{session_id}/events", dependencies=[Depends(authorized)])
async def events(session_id: UUID, request: Request):
    return await query(app.state.store.events, str(session_id), request.query_params.get("cursor"))
