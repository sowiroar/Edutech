import ast
import asyncio
import logging
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("module", ["rag_llamaindex.py", "rag_nexus.py"])
def test_document_client_starts_without_model_metadata_network(monkeypatch, module):
    """Exercise the real SDK constructor used by both RAGs, without credentials."""
    from unittest.mock import MagicMock

    from llama_index.llms.google_genai import GoogleGenAI

    from rag_config import document_generation_config

    client = MagicMock()
    client.models.get.side_effect = AssertionError("blocking metadata request")
    monkeypatch.setattr("google.genai.Client", lambda **_: client)
    tree = ast.parse((Path(__file__).parents[1] / "src" / module).read_text())
    constructor = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "GoogleGenAI"
    )
    llm = eval(
        compile(ast.Expression(constructor), module, "eval"),
        {
            "GoogleGenAI": GoogleGenAI,
            "api_key": "not-a-real-key",
            "document_generation_config": document_generation_config,
        },
    )
    client.models.get.assert_not_called()
    assert llm.metadata.context_window == 1_048_576
    assert llm.metadata.num_output == 65_536
    assert llm._generation_config["max_output_tokens"] is None
    assert llm._generation_config["thinking_config"]["thinking_budget"] == 512


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
