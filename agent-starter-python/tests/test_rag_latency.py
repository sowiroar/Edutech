import ast
import asyncio
import logging
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_document_generation_bounds_thinking_without_truncating_the_answer():
    from rag_config import document_generation_config

    config = document_generation_config()
    assert config.temperature == 0.2
    assert config.thinking_config is not None
    assert 0 < config.thinking_config.thinking_budget <= 512
    assert config.max_output_tokens is None


@pytest.mark.asyncio
async def test_cold_nexus_index_does_not_block_audio_event_loop():
    tree = ast.parse(
        (Path(__file__).parents[1] / "src/rag_nexus.py").read_text(encoding="utf-8")
    )
    query = next(
        n
        for n in tree.body
        if isinstance(n, ast.AsyncFunctionDef)
        and n.name == "consultar_especializacion_ia"
    )
    query.decorator_list = []
    heartbeat = asyncio.Event()
    responsive = []

    def initialize():
        time.sleep(0.05)
        responsive.append(heartbeat.is_set())
        return SimpleNamespace(query=lambda _: "grounded answer")

    env = {
        "asyncio": asyncio,
        "Any": object,
        "get_or_build_nexus_query_engine": initialize,
        "logger": logging.getLogger("test-rag"),
    }
    exec(
        compile(ast.Module(body=[query], type_ignores=[]), "production-rag", "exec"),
        env,
    )
    asyncio.get_running_loop().call_later(0.01, heartbeat.set)
    result = await env["consultar_especializacion_ia"]("test")
    assert responsive == [True]
    assert result == {"respuesta": "grounded answer", "fuentes": []}
