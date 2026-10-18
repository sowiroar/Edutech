"""Regresión (2026-10-18): GoogleGenAI(...) (el LLM de LlamaIndex, no el
RealtimeModel de Gemini Live) hace una llamada de red SÍNCRONA
(client.models.get(...)) para averiguar los límites reales del modelo cuando
falta `max_tokens` O `context_window` — los dos, confirmado en vivo que es un
"or": pasar solo uno no evita la llamada. En producción esa llamada se colgó
indefinidamente (DNS e IPv4/IPv6 funcionaban por separado, confirmado aparte)
y se comió el timeout completo de arranque de un worker nuevo (600s) sin
terminar nunca — mientras tanto ningún job nuevo podía atenderse, así que el
frontend dejaba de funcionar por completo tras el primer reinicio de proceso.

Estas pruebas no vuelven a reproducir el colgado (eso tardaría minutos y
dependería de la red real); verifican directamente que el código le pase
ambos argumentos a GoogleGenAI, que es lo único que evita la llamada."""

from __future__ import annotations

import pytest


def _assert_llm_built_without_hanging(monkeypatch, module_name: str, build_fn_name: str):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-para-la-prueba")
    module = __import__(module_name)

    captured: dict[str, object] = {}

    def fake_google_genai(*args, **kwargs):
        captured.update(kwargs)
        # Corte intencional: no hace falta que el resto de get_or_build_* corra de
        # verdad (construiría un índice real) para verificar los argumentos. El
        # try/except interno de esas funciones atrapa esto y devuelve None.
        raise RuntimeError("corte intencional de la prueba")

    monkeypatch.setattr("llama_index.llms.google_genai.GoogleGenAI", fake_google_genai)

    build_fn = getattr(module, build_fn_name)
    result = build_fn()

    assert result is None  # confirma que sí se llegó a construir el LLM (y se cortó ahí)
    assert captured.get("max_tokens") is not None, "max_tokens debe ir siempre, no solo a veces"
    assert captured.get("context_window") is not None, "context_window debe ir siempre, no solo a veces"


def test_rag_llamaindex_uam_passes_max_tokens_and_context_window(monkeypatch):
    import rag_llamaindex

    rag_llamaindex._uam_query_engine = None
    rag_llamaindex._uam_index = None
    _assert_llm_built_without_hanging(monkeypatch, "rag_llamaindex", "get_or_build_query_engine")


def test_rag_nexus_passes_max_tokens_and_context_window(monkeypatch):
    import rag_nexus

    rag_nexus._nexus_query_engine = None
    rag_nexus._nexus_index = None
    _assert_llm_built_without_hanging(monkeypatch, "rag_nexus", "get_or_build_nexus_query_engine")
