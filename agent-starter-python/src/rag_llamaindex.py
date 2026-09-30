"""Motor RAG Semántico para la Universidad Autónoma de Manizales (Elian).

Indexa documentos oficiales (reglamentos, estatutos, acuerdos, políticas) de la UAM
utilizando LlamaIndex y Google Gemini (models/gemini-embedding-2).
El índice vectorial se inicializa y persiste en disco una sola vez para evitar re-computar embeddings.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger("rag-uam")

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

_uam_index: Any = None
_uam_retriever: Any = None
_uam_query_engine: Any = None
_uam_lock = asyncio.Lock()


def _get_storage_dir() -> Path:
    storage_dir = os.getenv("UAM_STORAGE_DIR") or os.getenv("LLAMAINDEX_STORAGE_DIR")
    if not storage_dir:
        for candidate in [
            os.path.join(os.path.dirname(__file__), "..", "data", "uam_storage"),
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "uam_storage"),
            "/app/data/uam_storage",
            "/data/uam_storage",
        ]:
            if os.path.exists(candidate) and (Path(candidate) / "docstore.json").exists():
                storage_dir = candidate
                break
        else:
            storage_dir = os.path.join(os.path.dirname(__file__), "..", "data", "uam_storage")
    p = Path(storage_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_uam_docs_dir() -> Path:
    possible_paths = [
        os.getenv("UAM_DOCS_DIR", ""),
        os.path.join(os.path.dirname(__file__), "..", "data", "documentos_uam"),
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "documentos_uam"),
        "/app/data/documentos_uam",
        "/data/documentos_uam",
    ]
    for p_str in possible_paths:
        if p_str:
            p = Path(p_str).resolve()
            if p.is_dir() and any(p.iterdir()):
                return p
    return Path(os.path.join(os.path.dirname(__file__), "..", "data", "documentos_uam")).resolve()


def listar_documentos_uam() -> list[dict[str, Any]]:
    """Retorna la lista de todos los reglamentos y documentos oficiales de la UAM disponibles."""
    docs_dir = _get_uam_docs_dir()
    if not docs_dir.exists():
        return []

    catalogo = []
    for f in sorted(docs_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".doc", ".txt", ".md"]:
            catalogo.append(
                {
                    "nombre": f.name,
                    "tipo": f.suffix.lower().replace(".", "").upper(),
                    "tamano_kb": round(f.stat().st_size / 1024, 1),
                }
            )
    return catalogo


def _extraer_texto_archivo_uam(ruta: Path) -> str:
    """Extrae texto de archivos PDF o DOCX de forma tolerante a fallos con soporte multimodal."""
    sufijo = ruta.suffix.lower()
    texto = ""
    try:
        if sufijo == ".pdf":
            import pypdf

            reader = pypdf.PdfReader(str(ruta))
            paginas_texto = []
            for pag in reader.pages:
                t = pag.extract_text() or ""
                if t.strip():
                    paginas_texto.append(t)
            texto = "\n".join(paginas_texto)

            # Si el texto está vacío (PDF escaneado), se extrae automáticamente con Gemini multimodal
            if not texto.strip():
                logger.info("PDF escaneado detectado (%s). Extrayendo texto mediante Gemini multimodal...", ruta.name)
                api_key = os.getenv("GOOGLE_API_KEY")
                if api_key and api_key != "mock-key-for-tests":
                    try:
                        from google import genai

                        client = genai.Client(api_key=api_key)

                        # Evitar UnicodeEncodeError en httpx pasando un archivo temporal con nombre ASCII seguro
                        temp_file = None
                        upload_path = ruta
                        try:
                            str(ruta.name).encode("ascii")
                        except UnicodeEncodeError:
                            import shutil
                            import tempfile

                            temp_dir = Path(tempfile.gettempdir())
                            temp_file = temp_dir / f"uam_doc_{abs(hash(ruta.name))}.pdf"
                            shutil.copyfile(ruta, temp_file)
                            upload_path = temp_file

                        try:
                            uploaded = client.files.upload(file=str(upload_path))
                        finally:
                            if temp_file and temp_file.exists():
                                temp_file.unlink(missing_ok=True)

                        try:
                            res = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[
                                    uploaded,
                                    "Transcribe fielmente todo el contenido de este documento oficial respetando títulos, artículos, listas, tablas y requisitos sin omitir nada.",
                                ],
                            )
                            texto = res.text or ""
                            logger.info("Extracción multimodal completada para %s (%d caracteres)", ruta.name, len(texto))
                        finally:
                            try:
                                client.files.delete(name=uploaded.name)
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning("Fallo la extracción multimodal con Gemini para %s: %s", ruta.name, e)
                if not texto.strip():
                    texto = f"Documento oficial UAM: {ruta.stem}."
        elif sufijo in [".docx", ".doc"]:
            import docx

            doc = docx.Document(str(ruta))
            parrafos = [p.text for p in doc.paragraphs if p.text.strip()]
            texto = "\n".join(parrafos)
        elif sufijo in [".txt", ".md"]:
            texto = ruta.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        logger.exception("Error al leer archivo %s", ruta.name)

    return texto


def _cargar_documentos_uam():
    from llama_index.core import Document

    docs_dir = _get_uam_docs_dir()
    documentos = []

    if not docs_dir.exists():
        logger.warning("Directorio de documentos UAM no existe: %s", docs_dir)
        return []

    archivos = sorted(
        [f for f in docs_dir.iterdir() if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".doc", ".txt", ".md"]]
    )
    logger.info("Cargando %d archivos institucionales de la UAM desde %s", len(archivos), docs_dir)

    for ruta in archivos:
        contenido = _extraer_texto_archivo_uam(ruta)
        if not contenido or not contenido.strip():
            continue

        doc = Document(
            text=contenido,
            metadata={
                "archivo": ruta.name,
                "titulo": ruta.stem.replace("-", " ").replace("_", " ").title(),
                "fuente": "Documentos Oficiales UAM",
            },
        )
        documentos.append(doc)

    return documentos


def get_or_build_retriever():
    """Inicializa o recupera el retriever directo (sin segundo LLM) de LlamaIndex para Elian."""
    global _uam_index, _uam_retriever, _uam_query_engine
    if _uam_retriever is not None:
        return _uam_retriever

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key or api_key == "mock-key-for-tests":
        logger.warning("GOOGLE_API_KEY no disponible; RAG de Elian desactivado.")
        return None

    try:
        from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

        embed_model = GoogleGenAIEmbedding(
            model_name="models/gemini-embedding-2",
            api_key=api_key,
        )

        storage_dir = _get_storage_dir()
        docstore_file = storage_dir / "docstore.json"

        if docstore_file.exists():
            logger.info("Cargando índice persistente de la UAM desde %s", storage_dir)
            storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
            _uam_index = load_index_from_storage(storage_context, embed_model=embed_model)
        else:
            logger.info("Construyendo índice de embeddings de la UAM con SentenceSplitter(800)...")
            documentos = _cargar_documentos_uam()
            if not documentos:
                from llama_index.core import Document

                documentos = [
                    Document(
                        text="La Universidad Autónoma de Manizales (UAM) ofrece programas de pregrado en Fisioterapia, Odontología, Ingeniería Biomédica, Ingeniería de Sistemas, Ingeniería Industrial, Administración de Empresas, Economía, Negocios Internacionales y Diseño Industrial.",
                        metadata={"titulo": "Oferta Académica UAM", "archivo": "oferta-academica.pdf"},
                    ),
                    Document(
                        text="El Estatuto Profesoral de la UAM reglamenta el escalafón docente en cuatro categorías: Profesor Auxiliar, Profesor Asistente, Profesor Asociado y Profesor Titular. Para ser profesor auxiliar se requiere título profesional, 1 año de experiencia en la UAM, evaluación satisfactoria, inducción docente y TIC. Para profesor asistente se requiere título de posgrado y mínimo 2 años de experiencia como auxiliar.",
                        metadata={"titulo": "Estatuto Profesoral UAM", "archivo": "estatuto_profesoral_uam.pdf"},
                    ),
                ]

            splitter = SentenceSplitter(chunk_size=800, chunk_overlap=100)
            _uam_index = VectorStoreIndex.from_documents(
                documentos,
                embed_model=embed_model,
                transformations=[splitter],
            )
            _uam_index.storage_context.persist(persist_dir=str(storage_dir))
            logger.info("Índice de la UAM persistido exitosamente en %s", storage_dir)

        _uam_retriever = _uam_index.as_retriever(similarity_top_k=3)
        _uam_query_engine = _uam_retriever
        return _uam_retriever
    except Exception:
        logger.exception("Error al inicializar retriever de la UAM")
        return None


# Alias para compatibilidad
get_or_build_query_engine = get_or_build_retriever


async def consultar_uam(consulta: str) -> dict[str, Any] | None:
    """Ejecuta una consulta asíncrona híbrida ultra-rápida (BM25 local + Retriever semántico top_k=3) sin segundo LLM."""
    if not consulta or not consulta.strip():
        return None

    # 1. Búsqueda BM25 local (<5ms en SQLite FTS5)
    async def _consultar_bm25():
        try:
            try:
                from . import knowledge
            except ImportError:
                import knowledge

            return await asyncio.to_thread(knowledge.buscar, consulta, 2)
        except Exception:
            return []

    # 2. Búsqueda semántica vectorial directa (~250ms)
    async def _consultar_semantico():
        try:
            retriever = await asyncio.to_thread(get_or_build_retriever)
            if retriever is None:
                return []
            return await asyncio.to_thread(retriever.retrieve, consulta)
        except Exception:
            logger.exception("Error al recuperar nodos vectoriales de la UAM")
            return []

    # Ejecutar en paralelo sin añadir latencia extra
    resultados_bm25, nodos_vectoriales = await asyncio.gather(
        _consultar_bm25(),
        _consultar_semantico(),
    )

    if not resultados_bm25 and not nodos_vectoriales:
        return None

    fuentes: list[str] = []
    fragmentos: list[str] = []
    titulos_vistos: set[str] = set()

    # Priorizar nodo semántico principal y entrelazar con BM25
    candidatos: list[dict[str, str]] = []
    for node in nodos_vectoriales:
        meta = getattr(node.node, "metadata", {})
        archivo = meta.get("archivo") or meta.get("titulo") or "documento.pdf"
        titulo = meta.get("titulo") or meta.get("archivo") or "Documento UAM"
        texto = node.node.get_content().strip()
        candidatos.append({"titulo": titulo, "archivo": str(archivo), "texto": texto})

    for r in resultados_bm25:
        candidatos.append({
            "titulo": r.titulo,
            "archivo": getattr(r, "url", "") or f"{r.titulo}.pdf",
            "texto": r.texto.strip(),
        })

    for elem in candidatos:
        clave = elem["titulo"].lower().strip()
        if clave in titulos_vistos:
            continue
        titulos_vistos.add(clave)
        if elem["archivo"] and elem["archivo"] not in fuentes:
            fuentes.append(elem["archivo"])
        fragmentos.append(f"[{elem['titulo']}]:\n{elem['texto']}")
        if len(fragmentos) >= 3:
            break

    return {
        "respuesta": "\n\n".join(fragmentos),
        "fuentes": fuentes,
    }


# Alias para compatibilidad
consultar_uam_semantico = consultar_uam


