import asyncio

import pytest

from background_tasks import _pending, spawn_background


@pytest.mark.asyncio
async def test_task_is_retained_until_finished():
    gate = asyncio.Event()
    task = spawn_background(gate.wait())
    assert task in _pending
    gate.set()
    await task
    await asyncio.sleep(0)
    assert task not in _pending


@pytest.mark.asyncio
async def test_failure_is_observed_without_logging_payload(caplog):
    async def fail():
        raise ValueError("synthetic-private-payload")

    task = spawn_background(fail())
    with pytest.raises(ValueError):
        await task
    await asyncio.sleep(0)
    assert task not in _pending
    assert "ValueError" in caplog.text
    assert "synthetic-private-payload" not in caplog.text


@pytest.mark.asyncio
async def test_cancelled_task_is_released():
    task = spawn_background(asyncio.Event().wait())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)
    assert task not in _pending
