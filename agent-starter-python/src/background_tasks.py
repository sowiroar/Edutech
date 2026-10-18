"""Retain fire-and-forget work and observe failures without exposing payloads."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger("background-tasks")
_pending: set[asyncio.Task[Any]] = set()


def spawn_background(coroutine: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    task = asyncio.create_task(coroutine)
    _pending.add(task)

    def finished(done: asyncio.Task[Any]) -> None:
        _pending.discard(done)
        if not done.cancelled():
            error = done.exception()
            if error is not None:
                logger.warning("Background task failed: %s", type(error).__name__)

    task.add_done_callback(finished)
    return task
