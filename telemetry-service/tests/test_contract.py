from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from viva_metrics.contract import Event, context_fields, event_schema


def context():
    return {
        "app_session_id": str(uuid4()),
        "conversation_id": str(uuid4()),
        "anonymous_id": str(uuid4()),
        "identity_source": "visitor",
        "environment": "test",
        "release": "test",
        "presentation_mode": "voice",
        "room_name": "test-room",
        "participant_identity": "test-participant",
    }


def event(kind="session_started", payload=None, ctx=None):
    return {
        **context_fields(ctx or context()),
        "schema_version": 1,
        "event_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "source": "agent",
        "type": kind,
        "payload": payload or {},
    }


def test_contract_matches_exported_json_schema():
    from jsonschema import Draft202012Validator

    data = event()
    parsed = Event.model_validate(data).model_dump(mode="json")
    Draft202012Validator(event_schema()).validate(parsed)


@pytest.mark.parametrize(
    "changes",
    [
        {"payload": {"transcript": "not allowed"}},
        {"user_id": "student-chosen-by-browser"},
        {"occurred_at": "2026-10-17T12:00:00"},
        {"source": "unknown"},
        {"schema_version": 2},
    ],
)
def test_rejects_untrusted_or_sensitive_fields(changes):
    with pytest.raises(ValidationError):
        Event.model_validate({**event(), **changes})


def test_rejects_nonfinite_and_negative_measurements():
    for value in (float("nan"), float("inf"), -1):
        with pytest.raises(ValidationError):
            Event.model_validate(event("media_connected", {"elapsed_ms": value}))
