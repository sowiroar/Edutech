"""Versioned, content-free events. Never accept arbitrary telemetry payloads."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:/+ -]{1,192}$")]
Duration = Annotated[float, Field(ge=0, le=86_400_000, allow_inf_nan=False)]
Count = Annotated[int, Field(ge=0, le=10**12, strict=True)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionContext(StrictModel):
    app_session_id: UUID
    conversation_id: UUID
    anonymous_id: UUID
    user_id: None = None  # Moodle verification is deliberately not implemented.
    identity_source: Literal["visitor"] = "visitor"
    environment: Literal["local", "test", "uam-demo", "production"]
    release: Name = "unknown"
    avatar_release: Name | None = None
    presentation_mode: Literal["voice", "avatar"] = "voice"
    channel: Literal["voice"] = "voice"
    room_name: Name
    participant_identity: Name


def context_fields(context: dict) -> dict:
    return SessionContext.model_validate(context).model_dump(mode="json")


class StartPayload(StrictModel):
    model: Name | None = None


class EndPayload(StrictModel):
    reason: Literal["completed", "participant_left", "error", "shutdown", "expired", "unknown"]
    elapsed_ms: Duration | None = None


class AgentPayload(StrictModel):
    previous_agent_id: Name | None = None
    agent_id: Name


class ResponsePayload(StrictModel):
    source: Literal["say", "generate_reply", "realtime"] = "realtime"
    elapsed_ms: Duration | None = None
    server_response_start_ms: Duration | None = None
    boundary: Literal["speech_handle", "sdk_message"] = "speech_handle"


class ToolPayload(StrictModel):
    name: Name
    status: Literal["started", "ok", "error", "cancelled", "unknown"]
    elapsed_ms: Duration | None = None


class OperationPayload(StrictModel):
    purpose: Literal["rag", "memory", "embedding"]
    name: Name
    status: Literal["started", "ok", "error", "cancelled", "unknown"]
    elapsed_ms: Duration | None = None
    usage_observed: bool = False


class UsageEntry(StrictModel):
    unit: Literal["tokens", "seconds", "characters", "requests"] = "tokens"
    direction: Literal["input", "output"]
    modality: Literal["text", "audio", "image", "unspecified"]
    cached: bool = False
    quantity: Annotated[float, Field(ge=0, le=10**12, allow_inf_nan=False)]


class UsagePayload(StrictModel):
    provider: Name
    model: Name
    purpose: Literal["conversation", "rag", "memory", "embedding"]
    entries: list[UsageEntry] = Field(default_factory=list, max_length=24)
    accounting_source: Literal["provider", "derived", "unavailable"]
    coverage_reason: Literal[
        "complete", "modality_unknown", "usage_missing", "inconsistent", "estimated"
    ]
    counter_reset: bool = False
    snapshot_sequence: Count | None = None
    attempt: Annotated[int, Field(ge=1, le=1000)] | None = None


class ErrorPayload(StrictModel):
    component: Literal[
        "agent", "provider", "tool", "rag", "memory", "browser", "telemetry", "renderer"
    ]
    code: Name
    retryable: bool = False


class HealthPayload(StrictModel):
    enqueued: Count
    persisted: Count
    dropped: Count
    write_failed: Count
    queue_depth: Count
    queue_age_ms: Duration


class MediaPayload(StrictModel):
    elapsed_ms: Duration | None = None
    reason: (
        Literal[
            "connecting",
            "reconnecting",
            "disconnected",
            "unavailable",
            "error",
            "playing",
            "connected",
            "user",
        ]
        | None
    ) = None
    mode: Literal["voice", "avatar"] | None = None
    packets_lost: Count | None = None
    packets_received: Count | None = None
    jitter_ms: Duration | None = None
    round_trip_ms: Duration | None = None
    fps: Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)] | None = None


MEDIA_TYPES = {
    "media_connect_started",
    "media_connected",
    "audio_playback_started",
    "video_first_frame",
    "media_stalled",
    "media_recovered",
    "presentation_changed",
    "avatar_unavailable",
    "media_quality_sample",
    "media_disconnected",
}
PAYLOADS = {
    "session_started": StartPayload,
    "session_ended": EndPayload,
    "agent_changed": AgentPayload,
    "response_started": ResponsePayload,
    "response_completed": ResponsePayload,
    "response_interrupted": ResponsePayload,
    "tool_started": ToolPayload,
    "tool_completed": ToolPayload,
    "operation_started": OperationPayload,
    "operation_completed": OperationPayload,
    "usage_recorded": UsagePayload,
    "error": ErrorPayload,
    "producer_health": HealthPayload,
    **dict.fromkeys(sorted(MEDIA_TYPES), MediaPayload),
}


class Event(SessionContext):
    schema_version: Literal[1] = 1
    event_id: UUID
    occurred_at: datetime
    received_at: datetime | None = None
    source: Literal["agent", "browser", "bridge", "renderer", "collector"]
    turn_id: Name | None = None
    request_id: Name | None = None
    tool_call_id: Name | None = None
    media_session_id: UUID | None = None
    connection_attempt_id: UUID | None = None
    agent_id: Name | None = None
    avatar_id: Name | None = None
    trace_id: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")] | None = None
    span_id: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{16}$")] | None = None
    type: str
    payload: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_envelope(self):
        if self.occurred_at.tzinfo is None:
            raise ValueError("Timezone required")
        self.occurred_at = self.occurred_at.astimezone(timezone.utc)
        if self.type not in PAYLOADS:
            raise ValueError("Unknown event type")
        self.payload = PAYLOADS[self.type].model_validate(self.payload).model_dump(mode="json")
        if self.source == "collector" and (
            self.type != "session_ended" or self.payload["reason"] != "expired"
        ):
            raise ValueError("Collector only emits expiration")
        if self.source not in ("agent", "collector") and self.type not in MEDIA_TYPES:
            raise ValueError("Media producers cannot emit agent usage or lifecycle")
        return self


def event_schema() -> dict:
    schema = Event.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:vivaverse:telemetry-event:1"
    schema["properties"]["type"]["enum"] = list(PAYLOADS)
    definitions = schema.setdefault("$defs", {})
    schema["allOf"] = [
        {
            "if": {"properties": {"source": {"enum": ["browser", "bridge", "renderer"]}}},
            "then": {"properties": {"type": {"enum": sorted(MEDIA_TYPES)}}},
        },
        {
            "if": {"properties": {"source": {"const": "collector"}}},
            "then": {
                "properties": {
                    "type": {"const": "session_ended"},
                    "payload": {"properties": {"reason": {"const": "expired"}}},
                }
            },
        },
    ]
    for name, model in PAYLOADS.items():
        payload = model.model_json_schema()
        definitions.update(payload.pop("$defs", {}))
        definitions[model.__name__] = payload
        schema["allOf"].append(
            {
                "if": {"properties": {"type": {"const": name}}, "required": ["type"]},
                "then": {"properties": {"payload": {"$ref": f"#/$defs/{model.__name__}"}}},
            }
        )
    return schema
