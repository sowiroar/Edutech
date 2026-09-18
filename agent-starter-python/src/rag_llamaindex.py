"""Motor RAG Semántico con LlamaIndex para documentos oficiales y guías de la UAM.

Carga los fragmentos de conocimiento o documentos oficiales, genera embeddings con
Google Gemini (models/gemini-embedding-001) y construye un VectorStoreIndex persistente
para consultas de lenguaje natural en tiempo real con LiveKit.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger("rag-llamaindex")

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

_index: Any = None
_query_engine: Any = None
_lock = asyncio.Lock()


def _get_storage_dir() -> Path:
    storage_dir = os.getenv("LLAMAINDEX_STORAGE_DIR")
    if not storage_dir:
        storage_dir = os.path.join(os.path.dirname(__file__), "..", "data", "llamaindex_storage")
    p = Path(storage_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_knowledge_db_path() -> Path | None:
    # Busca la base de datos de conocimiento generada por knowledge-sync
    possible_paths = [
        os.getenv("KNOWLEDGE_DB", ""),
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge.db"),
        os.path.join(os.path.dirname(__file__), "..", "data", "knowledge.db"),
        "/data/knowledge.db",
    ]
    for path_str in possible_paths:
        if path_str:
            p = Path(path_str).resolve()
            if p.is_file():
                return p
    return None


def _load_documents_from_db():
    from llama_index.core import Document

    db_path = _get_knowledge_db_path()
    if not db_path or not db_path.is_file():
        logger.warning("No se encontró base de datos knowledge.db para indexar en LlamaIndex.")
        return []

    documents = []
    try:
        conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
        cursor = conn.cursor()
        filas = cursor.execute(
            "SELECT titulo, texto, fuente, categoria, url, privado FROM fragmentos"
        ).fetchall()
        conn.close()

        for titulo, texto, fuente, categoria, url, privado in filas:
            if not texto or not texto.strip():
                continue
            doc = Document(
                text=texto,
                metadata={
                    "titulo": titulo or "",
                    "fuente": fuente or "",
                    "categoria": categoria or "",
                    "url": url or "",
                    "privado": bool(int(privado)),
                },
                excluded_llm_metadata_keys=["url", "privado"],
                excluded_embed_metadata_keys=["url", "privado"],
            )
            documents.append(doc)
        logger.info("Cargados %d fragmentos de conocimiento desde %s", len(documents), db_path)
    except Exception:
        logger.exception("Error al leer fragmentos de knowledge.db")

    return documents


def get_or_build_query_engine():
    """Inicializa o recupera el query_engine asíncrono de LlamaIndex."""
    global _index, _query_engine
    if _query_engine is not None:
        return _query_engine

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key or api_key == "mock-key-for-tests":
        logger.warning("GOOGLE_API_KEY no configurada o mock; RAG semántico no inicializado.")
        return None

    try:
        from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
        from llama_index.llms.google_genai import GoogleGenAI

        # Configurar Embeddings y LLM de Google
        embed_model = GoogleGenAIEmbedding(
            model_name="models/gemini-embedding-2",
            api_key=api_key,
        )
        llm = GoogleGenAI(
            model="models/gemini-2.5-flash",
            api_key=api_key,
            temperature=0.2,
        )

        storage_dir = _get_storage_dir()
        docstore_file = storage_dir / "docstore.json"

        if docstore_file.exists():
            logger.info("Cargando índice LlamaIndex existente desde %s", storage_dir)
            storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
            _index = load_index_from_storage(
                storage_context,
                embed_model=embed_model,
            )
        else:
            logger.info("Construyendo nuevo índice LlamaIndex...")
            documents = _load_documents_from_db()
            if not documents:
                # Documentos de fallback si la base de datos aún no sincronizó
                from llama_index.core import Document
                documents = [
                    Document(
                        text="La Universidad Autónoma de Manizales (UAM) ofrece programas de pregrado en Fisioterapia, Odontología, Ingeniería Biomédica, Ingeniería de Sistemas, Ingeniería Industrial, Administración de Empresas, Economía, Negocios Internacionales y Diseño Industrial.",
                        metadata={"titulo": "Oferta Académica UAM", "fuente": "Portal UAM", "categoria": "Programas"},
                    ),
                    Document(
                        text="El proceso de matrícula en la UAM se realiza a través del portal institucional IntraUAM con las credenciales de estudiante.",
                        metadata={"titulo": "Matrícula Institucional", "fuente": "Guía Estudiantil", "categoria": "Trámites"},
                    ),
                ]

            _index = VectorStoreIndex.from_documents(
                documents,
                embed_model=embed_model,
            )
            _index.storage_context.persist(persist_dir=str(storage_dir))
            logger.info("Índice LlamaIndex persistido con éxito en %s", storage_dir)

        _query_engine = _index.as_query_engine(
            llm=llm,
            similarity_top_k=3,
        )
        return _query_engine
    except Exception:
        logger.exception("Error al inicializar query_engine de LlamaIndex")
        return None


async def consultar_uam_semantico(consulta: str) -> str | None:
    """Ejecuta una consulta semántica usando LlamaIndex.
    
    Retorna la respuesta generada a partir de los fragmentos recuperados,
    o None si el motor no está disponible.
    """
    if not consulta.strip():
        return None

    engine = get_or_build_query_engine()
    if engine is None:
        return None

    def _sync_query():
        try:
            response = engine.query(consulta)
            return str(response)
        except Exception:
            logger.exception("Error al consultar LlamaIndex con query: %s", consulta)
            return None

    return await asyncio.to_thread(_sync_query)

