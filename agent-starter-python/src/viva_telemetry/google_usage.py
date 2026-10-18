"""Wrap only clients owned by this application; never patch the SDK globally.

Nonstreaming RAG/Mem0 calls keep the exact return object and exception. Bootstrap
outside a signed conversation and provider-internal retries have no session cost
attribution. Missing usage is explicit, never estimated from prompt text.
"""

import contextvars
import inspect
from uuid import uuid4

from . import current

operation = contextvars.ContextVar("telemetry_operation", default=None)


def record(response, model, purpose):
    emitter = current.get()
    if emitter is None:
        return
    metadata = getattr(response, "usage_metadata", None)
    values = metadata.model_dump() if hasattr(metadata, "model_dump") else metadata
    values = values if isinstance(values, dict) else {}
    entries = []
    prompt = values.get("prompt_token_count")
    cached = values.get("cached_content_token_count") or 0
    # This adapter is only attached to text RAG/Mem0, not realtime audio.
    output = values.get("candidates_token_count")
    thoughts = values.get("thoughts_token_count") or 0
    if prompt is not None:
        entries.append(
            {
                "unit": "tokens",
                "direction": "input",
                "modality": "text",
                "cached": False,
                "quantity": max(0, prompt - cached),
            }
        )
        if cached:
            entries.append(
                {
                    "unit": "tokens",
                    "direction": "input",
                    "modality": "text",
                    "cached": True,
                    "quantity": cached,
                }
            )
    if output is not None:
        entries.append(
            {
                "unit": "tokens",
                "direction": "output",
                "modality": "text",
                "cached": False,
                "quantity": output + thoughts,
            }
        )
    observed = bool(entries)
    scope = operation.get()
    if scope is not None:
        scope["calls"] += 1
        scope["missing"] += int(not observed)
    emitter.thread_emit(
        "usage_recorded",
        {
            "provider": "google",
            "model": model.removeprefix("models/"),
            "purpose": purpose,
            "entries": entries,
            "accounting_source": "provider" if observed else "unavailable",
            "coverage_reason": "complete" if observed else "usage_missing",
        },
        request_id=str(getattr(response, "response_id", None) or uuid4()),
    )


class Proxy:
    def __init__(self, target, purpose, model=None):
        self.target = target
        self.purpose = purpose
        self.model = model

    def __getattr__(self, name):
        target = getattr(self.target, name)
        if name in ("models", "aio", "chats"):
            return Proxy(target, self.purpose, self.model)
        if name == "create":

            def create(*args, **kwargs):
                return Proxy(
                    target(*args, **kwargs),
                    self.purpose,
                    kwargs.get("model", self.model),
                )

            return create
        if name not in ("generate_content", "embed_content", "send_message"):
            return target
        purpose = "embedding" if name == "embed_content" else self.purpose

        def capture(result, kwargs):
            try:
                record(result, kwargs.get("model", self.model) or "unknown", purpose)
            except Exception:
                emitter = current.get()
                if emitter:
                    emitter.thread_emit(
                        "error",
                        {
                            "component": "telemetry",
                            "code": "ProviderUsageAdapterError",
                            "retryable": False,
                        },
                    )
            return result

        if inspect.iscoroutinefunction(target):

            async def call_async(*args, **kwargs):
                return capture(await target(*args, **kwargs), kwargs)

            return call_async

        def call(*args, **kwargs):
            return capture(target(*args, **kwargs), kwargs)

        return call


def wrap_client(client, purpose):
    return client if isinstance(client, Proxy) else Proxy(client, purpose)
