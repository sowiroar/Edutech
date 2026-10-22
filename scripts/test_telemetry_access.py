#!/usr/bin/env python3
"""Local HTTP access smoke; token issuance only, no model calls."""

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:3500"


async def main(output):
    values = {
        k: v.strip().strip("\"'")
        for line in (ROOT / ".env.voice").read_text().splitlines()
        if "=" in line and not line.startswith("#")
        for k, v in [line.split("=", 1)]
    }
    result = {}
    async with (
        httpx.AsyncClient(base_url=BASE, headers={"Origin": BASE}) as admin,
        httpx.AsyncClient(base_url=BASE, headers={"Origin": BASE}) as visitor,
    ):
        r = await admin.get("/api/admin/metrics")
        assert r.status_code == 401
        result["anonymous_admin_rejected"] = True
        r = await admin.post(
            "/api/admin/login",
            json={"password": "invalid"},
            headers={"Origin": "https://invalid.test"},
        )
        assert r.status_code == 403
        result["cross_origin_rejected"] = True
        r = await admin.post(
            "/api/admin/login", json={"password": values["TELEMETRY_ADMIN_PASSWORD"]}
        )
        assert r.status_code == 200
        result["admin_cookie_httponly"] = "HttpOnly" in r.headers.get("set-cookie", "")
        a = (
            await visitor.post(
                "/api/token",
                json={
                    "user_id": "FORGED",
                    "room_config": {"agents": [{"agentName": "FORGED"}]},
                },
            )
        ).json()["telemetry"]
        b = (await visitor.post("/api/token", json={})).json()["telemetry"]
        c = (await admin.post("/api/token", json={})).json()["telemetry"]
        assert (
            a["context"]["anonymous_id"]
            == b["context"]["anonymous_id"]
            != c["context"]["anonymous_id"]
        )
        assert a["context"]["app_session_id"] != b["context"]["app_session_id"]
        assert a["context"]["user_id"] is None
        result["visitor_and_session_isolation"] = True
        event = dict(
            event_id=str(uuid4()),
            occurred_at=datetime.now(timezone.utc).isoformat(),
            type="media_connected",
            payload={"elapsed_ms": 10},
        )
        r = await visitor.post(
            "/api/telemetry/media",
            json={
                "context_token": a["token"],
                "events": [dict(event, app_session_id=c["context"]["app_session_id"])],
            },
        )
        assert r.status_code == 400
        result["foreign_session_rejected"] = True
        r = await visitor.post(
            "/api/telemetry/media",
            json={
                "context_token": a["token"],
                "events": [dict(event, type="usage_recorded")],
            },
        )
        assert r.status_code == 400
        result["client_cost_event_rejected"] = True
        r = await visitor.post(
            "/api/telemetry/media",
            json={
                "context_token": a["token"],
                "events": [dict(event, type="conversation_message")],
            },
        )
        assert r.status_code == 400
        result["client_transcript_rejected"] = True
        r = await visitor.post(
            "/api/telemetry/media", json={"context_token": "invalid", "events": [event]}
        )
        assert r.status_code == 400
        result["unsigned_context_rejected"] = True
        r = await visitor.post(
            "/api/telemetry/media",
            json={"context_token": a["token"], "events": [event]},
        )
        assert r.status_code == 409
        result["start_required"] = True
        r = await admin.get("/api/admin/metrics?environment=invalid")
        assert r.status_code == 422
        result["invalid_filter_rejected"] = True
        r = await admin.get("/api/admin/metrics?environment=test")
        assert r.status_code == 200
        result["test_environment_sessions"] = r.json()["summary"]["sessions"]
        r = await admin.get("/api/admin/sessions")
        assert r.status_code == 200
        sessions = r.json()["items"]
        if sessions:
            r = await visitor.get(
                "/api/admin/sessions/" + sessions[0]["id"] + "/events"
            )
            assert r.status_code == 401
            result["foreign_session_read_rejected"] = True
        await admin.post("/api/admin/logout")
        assert (await admin.get("/api/admin/metrics")).status_code == 401
        result["logout_revokes_cookie"] = True
    print(json.dumps(result))
    Path(output).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs/validation/2026-10-17-telemetry/http-access.json"),
    )
    asyncio.run(main(parser.parse_args().output))
