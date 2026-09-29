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
_uam_query_engine: Any = None
_uam_lock = asyncio.Lock()

# Plantilla de síntesis: pide concisión SOLO cuando la respuesta es puntual, sin
# imponer un tope de longitud fijo ni forzar el idioma (el modelo ya responde en
# español porque así se le habla). La latencia de un LLM depende sobre todo de
# cuánto genera, así que evitar relleno innecesario ayuda sin sacrificar
# información cuando la pregunta sí la requiere (Claude, 2026-09-29).
_QA_TEMPLATE_UAM = None


def _get_qa_template_uam():
    global _QA_TEMPLATE_UAM
    if _QA_TEMPLATE_UAM is None:
        from llama_index.core import PromptTemplate

        _QA_TEMPLATE_UAM = PromptTemplate(
            "La siguiente es información de contexto extraída de documentos oficiales de la UAM.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Con base únicamente en esa información (no uses conocimiento previo), responde "
            "la consulta como si hablaras en una conversación oral: en prosa continua, sin "
            "markdown, viñetas ni encabezados. Sé conciso cuando la respuesta sea puntual y "
            "simple; si la pregunta requiere explicar varios puntos, una lista de elementos "
            "o una comparación, exprésalo con la extensión que haga falta para cubrirlo bien, "
            "sin omitir información relevante solo por acortar.\n"
            "Consulta: {query_str}\n"
            "Respuesta: "
        )
    return _QA_TEMPLATE_UAM


def _get_storage_dir() -> Path:
    storage_dir = os.getenv("UAM_STORAGE_DIR") or os.getenv("LLAMAINDEX_STORAGE_DIR")
    if not storage_dir:
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
                            import time

                            intentos_max = 3
                            for intento in range(1, intentos_max + 1):
                                try:
                                    res = client.models.generate_content(
                                        model="gemini-2.5-flash",
                                        contents=[
                                            uploaded,
                                            "Transcribe fielmente todo el contenido de este documento oficial respetando títulos, artículos, listas, tablas y requisitos sin omitir nada.",
                                        ],
                                    )
                                    texto = res.text or ""
                                    logger.info(
                                        "Extracción multimodal completada para %s (%d caracteres, intento %d/%d)",
                                        ruta.name,
                                        len(texto),
                                        intento,
                                        intentos_max,
                                    )
                                    break
                                except Exception as e:
                                    if intento == intentos_max:
                                        raise
                                    espera = 2**intento
                                    logger.warning(
                                        "Extracción multimodal falló para %s (intento %d/%d): %s. Reintentando en %ds...",
                                        ruta.name,
                                        intento,
                                        intentos_max,
                                        e,
                                        espera,
                                    )
                                    time.sleep(espera)
                        finally:
                            try:
                                client.files.delete(name=uploaded.name)
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning("Fallo la extracción multimodal con Gemini para %s tras varios reintentos: %s", ruta.name, e)
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


def get_or_build_query_engine():
    """Inicializa o recupera el query_engine asíncrono de LlamaIndex para Elian."""
    global _uam_index, _uam_query_engine
    if _uam_query_engine is not None:
        return _uam_query_engine

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key or api_key == "mock-key-for-tests":
        logger.warning("GOOGLE_API_KEY no disponible; RAG de Elian desactivado.")
        return None

    try:
        from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
        from llama_index.llms.google_genai import GoogleGenAI

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
            logger.info("Cargando índice persistente de la UAM desde %s", storage_dir)
            storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
            _uam_index = load_index_from_storage(storage_context, embed_model=embed_model)
        else:
            logger.info("Construyendo índice de embeddings de la UAM por primera vez...")
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

            _uam_index = VectorStoreIndex.from_documents(documentos, embed_model=embed_model)
            _uam_index.storage_context.persist(persist_dir=str(storage_dir))
            logger.info("Índice de la UAM persistido exitosamente en %s", storage_dir)

        _uam_query_engine = _uam_index.as_query_engine(
            llm=llm,
            similarity_top_k=4,
            text_qa_template=_get_qa_template_uam(),
        )
        return _uam_query_engine
    except Exception:
        logger.exception("Error al inicializar query_engine de la UAM")
        return None


async def consultar_uam(consulta: str) -> dict[str, Any] | None:
    """Ejecuta una consulta asíncrona sobre la base de conocimiento de la UAM sin bloquear el event loop."""
    if not consulta.strip():
        return None

    engine = await asyncio.to_thread(get_or_build_query_engine)
    if engine is None:
        return None

    def _sync_query():
        try:
            response = engine.query(consulta)
            fuentes = []
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    meta = getattr(node.node, "metadata", {})
                    archivo = meta.get("archivo") or meta.get("titulo")
                    if archivo and archivo not in fuentes:
                        fuentes.append(archivo)
            return {
                "respuesta": str(response).strip(),
                "fuentes": fuentes,
            }
        except Exception:
            logger.exception("Error al consultar RAG de la UAM: %s", consulta)
            return None

    return await asyncio.to_thread(_sync_query)


# Alias para compatibilidad
consultar_uam_semantico = consultar_uam


