"""Gestor de memoria de largo plazo con Mem0 para agentes de voz LiveKit.

Utiliza Mem0 con Qdrant (servidor, no embebido) y Google Gemini (LLM + Embeddings)
para almacenar y recuperar recuerdos, preferencias y contexto del estudiante entre turnos y sesiones.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

logger = logging.getLogger("memory-manager")

_memory_instance: Any = None
_init_lock = asyncio.Lock()

# Bug real encontrado el 2026-10-08: /app/data/mem0 nunca tuvo volumen
# montado (ver docker-compose.yml), asi que get_memory_instance() fallaba
# por permisos en CADA llamada — y como solo cacheaba el EXITO, reintentaba
# la inicializacion completa (incluida la importacion de qdrant_client, que
# por si sola bloquea el event loop ~1s) en cada turno de cada llamada.
# Ya se corrigio el volumen, pero se cachea tambien el fallo (con
# enfriamiento, no permanente) para que un problema futuro no vuelva a
# convertirse en ~1s de bloqueo repetido por turno.
_ultimo_fallo: float = 0.0
_FALLO_COOLDOWN_SEGUNDOS = 30.0


def _get_mem0_config() -> dict[str, Any]:
    api_key = os.getenv("GOOGLE_API_KEY", "")

    return {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                # Servidor Qdrant, no el modo local/embebido (bug real
                # encontrado el 2026-10-08: el modo local toma un lock
                # exclusivo del archivo de storage — en cuanto hay una
                # llamada real activa, LiveKit levanta un segundo proceso
                # worker (num_idle_processes=1 deja uno de repuesto listo
                # para la siguiente llamada) y ese segundo proceso no podia
                # abrir el mismo storage: "already accessed by another
                # instance of Qdrant client". El servidor si soporta
                # multiples procesos concurrentes, que es justo lo que
                # este despliegue necesita.
                "host": os.getenv("QDRANT_HOST", "qdrant"),
                "port": int(os.getenv("QDRANT_PORT", "6333")),
                "embedding_model_dims": 768,
            },
        },
        "llm": {
            "provider": "gemini",
            "config": {
                "model": "gemini-2.5-flash",
                "api_key": api_key,
                "temperature": 0.2,
                "max_tokens": 1000,
            },
        },
        "embedder": {
            "provider": "gemini",
            "config": {
                "model": "models/gemini-embedding-2",
                "api_key": api_key,
                "embedding_dims": 768,
            },
        },
    }


def get_memory_instance():
    """Retorna la instancia singleton de Mem0 Memory."""
    global _memory_instance, _ultimo_fallo
    if _memory_instance is not None:
        return _memory_instance

    if _ultimo_fallo and (time.monotonic() - _ultimo_fallo) < _FALLO_COOLDOWN_SEGUNDOS:
        return None  # fallo reciente: no reintentar la inicializacion pesada todavia

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key or api_key == "mock-key-for-tests":
        logger.warning("GOOGLE_API_KEY no disponible o mock; memoria persistente desactivada.")
        return None

    try:
        from mem0 import Memory

        config = _get_mem0_config()
        _memory_instance = Memory.from_config(config)
        logger.info("Instancia de Mem0 inicializada con éxito usando Qdrant y Gemini.")
        return _memory_instance
    except Exception:
        logger.exception("Error al inicializar la instancia de Mem0")
        _ultimo_fallo = time.monotonic()
        return None


async def guardar_memoria_usuario(user_id: str, mensaje: str, metadata: dict[str, Any] | None = None) -> None:
    """Guarda un recuerdo o interacción relevante del usuario en memoria persistente."""
    if not user_id or not mensaje.strip():
        return

    mem = get_memory_instance()
    if mem is None:
        return

    def _sync_add():
        try:
            mem.add(
                mensaje,
                user_id=user_id,
                metadata=metadata or {},
            )
            logger.info("Recuerdo guardado con éxito para usuario %s", user_id)
        except Exception:
            logger.exception("Error al guardar memoria en Mem0 para usuario %s", user_id)

    await asyncio.to_thread(_sync_add)


async def buscar_memorias_usuario(user_id: str, consulta: str, limite: int = 5) -> list[str]:
    """Busca recuerdos existentes del usuario relevantes para la consulta dada."""
    if not user_id or not consulta.strip():
        return []

    mem = get_memory_instance()
    if mem is None:
        return []

    def _sync_search() -> list[str]:
        try:
            # Mem0 local Qdrant busca usando filters={'user_id': user_id}
            resultados = mem.search(
                query=consulta,
                limit=limite,
                filters={"user_id": user_id},
            )
            recuerdos = []
            if isinstance(resultados, dict) and "results" in resultados:
                items = resultados["results"]
            elif isinstance(resultados, list):
                items = resultados
            else:
                items = []

            for item in items:
                if isinstance(item, dict):
                    texto = item.get("memory") or item.get("text")
                    if texto:
                        recuerdos.append(str(texto))
                elif isinstance(item, str):
                    recuerdos.append(item)
            return recuerdos
        except Exception:
            logger.exception("Error al buscar memorias en Mem0 para usuario %s", user_id)
            return []

    return await asyncio.to_thread(_sync_search)


async def formatear_contexto_memoria(user_id: str, consulta: str) -> str:
    """Genera un bloque de texto formateado con las memorias previas del usuario para inyectar al LLM."""
    recuerdos = await buscar_memorias_usuario(user_id, consulta, limite=4)
    if not recuerdos:
        return ""

    lineas = ["\n[RECUERDOS Y PREFERENCIAS PREVIAS DEL ESTUDIANTE]:"]
    for r in recuerdos:
        lineas.append(f"- {r}")
    lineas.append(
        "Utiliza esta información para personalizar tu respuesta y demostrar que recuerdas al usuario, pero solo si es pertinente a la conversación.\n"
    )
    return "\n".join(lineas)
