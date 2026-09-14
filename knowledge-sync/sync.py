"""Sincroniza las fuentes de conocimiento de la UAM en un índice de búsqueda.

Fuentes:
  - Documentos UAM (reglamentos, acuerdos, políticas): se descargan con
    descargar_documentos_uam.py y se extrae el texto de los PDF.
  - Portal de Conocimiento (WordPress REST con contraseña de aplicación):
    guías de trámites y soporte. Las entradas privadas solo exponen título y enlace.

Salida: base SQLite con la tabla FTS5 ``fragmentos`` que consulta el agente Elian
(agent-starter-python/src/knowledge.py). El índice se construye en un archivo
temporal y se reemplaza de forma atómica, así el agente nunca lee uno a medias.
"""

from __future__ import annotations

import csv
import html
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import requests
from bs4 import BeautifulSoup

from descargar_documentos_uam import URL_INICIAL, descargar_documentos

logger = logging.getLogger("knowledge-sync")

PORTAL_URL_POR_DEFECTO = "https://portalconocimiento.autonoma.edu.co"
AVISO_PRIVADO = "members-access-error"

# Contrato con agent-starter-python/src/knowledge.py: no cambiar columnas sin actualizarlo.
ESQUEMA = """
CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE VIRTUAL TABLE fragmentos USING fts5(
    titulo,
    texto,
    fuente UNINDEXED,
    categoria UNINDEXED,
    url UNINDEXED,
    privado UNINDEXED,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


@dataclass
class Registro:
    fuente: str
    titulo: str
    texto: str
    categoria: str = ""
    url: str = ""
    privado: bool = False


def limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def html_a_texto(contenido: str) -> str:
    return limpiar(BeautifulSoup(contenido or "", "html.parser").get_text(" "))


def fragmentar(texto: str, palabras: int = 180, solape: int = 40) -> list[str]:
    """Divide el texto en fragmentos de ``palabras`` con ``solape`` entre vecinos."""
    tokens = texto.split()
    if not tokens:
        return []
    paso = max(1, palabras - solape)
    inicios = range(0, max(len(tokens) - solape, 1), paso)
    return [" ".join(tokens[inicio : inicio + palabras]) for inicio in inicios]


def extraer_texto_pdf(ruta: Path) -> str:
    try:
        with pymupdf.open(ruta) as documento:
            return limpiar(" ".join(pagina.get_text() for pagina in documento))
    except Exception as exc:
        logger.warning("No se pudo extraer texto de %s: %s", ruta.name, exc)
        return ""


def leer_documentos_uam(directorio: Path, url: str = URL_INICIAL) -> list[Registro]:
    """Descarga (incremental) los Documentos UAM y devuelve su texto."""
    ruta_csv = directorio / "documentos_uam.csv"
    descargar_documentos(url, directorio, ruta_csv)

    registros = []
    with ruta_csv.open(encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            ruta = directorio / fila["nombre_archivo"]
            es_pdf = ruta.suffix.lower() == ".pdf" and ruta.is_file()
            registros.append(
                Registro(
                    fuente="Documentos UAM",
                    titulo=limpiar(fila["titulo"]),
                    texto=extraer_texto_pdf(ruta) if es_pdf else "",
                    categoria=limpiar(f"{fila['categoria']} - {fila['origen']}"),
                    url=url,
                )
            )
    return registros


def registro_desde_post(post: dict) -> Registro:
    contenido = post.get("content", {}).get("rendered", "")
    privado = AVISO_PRIVADO in contenido

    terminos: list[str] = []
    for grupo in post.get("_embedded", {}).get("wp:term", []):
        for termino in grupo:
            nombre = html.unescape(termino.get("name", ""))
            if nombre and nombre not in terminos:
                terminos.append(nombre)

    return Registro(
        fuente="Portal de Conocimiento",
        titulo=html_a_texto(post.get("title", {}).get("rendered", "")),
        texto="" if privado else html_a_texto(contenido),
        categoria=", ".join(terminos),
        url=post.get("link", ""),
        privado=privado,
    )


def leer_portal_conocimiento(
    url_base: str, usuario: str, clave: str, timeout: int = 60
) -> list[Registro]:
    """Recorre todas las páginas de /wp-json/wp/v2/posts con Basic Auth."""
    endpoint = url_base.rstrip("/") + "/wp-json/wp/v2/posts"
    registros: list[Registro] = []
    pagina = total_paginas = 1

    with requests.Session() as sesion:
        sesion.auth = (usuario, clave)
        sesion.headers["User-Agent"] = "edutech-knowledge-sync"
        while pagina <= total_paginas:
            respuesta = sesion.get(
                endpoint,
                params={"per_page": 100, "page": pagina, "_embed": 1},
                timeout=timeout,
            )
            respuesta.raise_for_status()
            total_paginas = int(respuesta.headers.get("X-WP-TotalPages", "1"))
            registros.extend(registro_desde_post(post) for post in respuesta.json())
            pagina += 1
    return registros


def construir_indice(registros: list[Registro], ruta_db: Path) -> int:
    """Crea el índice FTS5 y lo publica de forma atómica. Devuelve los fragmentos."""
    ruta_db.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta_db.with_suffix(".tmp")
    temporal.unlink(missing_ok=True)

    total = 0
    conexion = sqlite3.connect(temporal)
    try:
        conexion.executescript(ESQUEMA)
        for registro in registros:
            for fragmento in fragmentar(registro.texto) or [""]:
                conexion.execute(
                    "INSERT INTO fragmentos (titulo, texto, fuente, categoria, url, privado)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        registro.titulo,
                        fragmento,
                        registro.fuente,
                        registro.categoria,
                        registro.url,
                        int(registro.privado),
                    ),
                )
                total += 1
        conexion.executemany(
            "INSERT INTO meta VALUES (?, ?)",
            [
                ("actualizado", datetime.now(UTC).isoformat()),
                ("registros", str(len(registros))),
                ("fragmentos", str(total)),
            ],
        )
        conexion.commit()
    finally:
        conexion.close()

    os.replace(temporal, ruta_db)
    return total


def sincronizar(directorio_datos: Path, portal: tuple[str, str, str] | None) -> bool:
    """Actualiza el índice. Si alguna fuente falla, conserva el índice anterior."""
    registros: list[Registro] = []
    fallidas: list[str] = []

    try:
        documentos = leer_documentos_uam(
            directorio_datos / "documentos_uam",
            os.getenv("DOCUMENTOS_UAM_URL", URL_INICIAL),
        )
        registros += documentos
        logger.info("Documentos UAM: %d documentos", len(documentos))
    except Exception:
        logger.exception("Falló la sincronización de Documentos UAM")
        fallidas.append("Documentos UAM")

    if portal:
        try:
            entradas = leer_portal_conocimiento(*portal)
            registros += entradas
            privadas = sum(entrada.privado for entrada in entradas)
            logger.info(
                "Portal de Conocimiento: %d entradas (%d privadas, solo título)",
                len(entradas),
                privadas,
            )
        except Exception:
            logger.exception("Falló la sincronización del Portal de Conocimiento")
            fallidas.append("Portal de Conocimiento")
    else:
        logger.warning(
            "Sin credenciales del Portal de Conocimiento: se omite esa fuente"
        )

    ruta_db = directorio_datos / "knowledge.db"
    if fallidas and ruta_db.exists():
        logger.error(
            "Fuentes con error (%s): se conserva el índice anterior",
            ", ".join(fallidas),
        )
        return False
    if not registros:
        logger.error("No se obtuvo ningún registro: no se construye el índice")
        return False

    total = construir_indice(registros, ruta_db)
    logger.info(
        "Índice actualizado: %d registros, %d fragmentos", len(registros), total
    )
    return True


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    directorio = Path(os.getenv("DATA_DIR", "/data"))
    intervalo_horas = float(os.getenv("SYNC_INTERVAL_HOURS", "24"))

    usuario = os.getenv("PORTAL_CONOCIMIENTO_USER", "")
    clave = os.getenv("PORTAL_CONOCIMIENTO_APP_PASSWORD", "")
    portal = None
    if usuario and clave:
        url = os.getenv("PORTAL_CONOCIMIENTO_URL") or PORTAL_URL_POR_DEFECTO
        portal = (url, usuario, clave)

    while True:
        sincronizar(directorio, portal)
        if intervalo_horas <= 0:
            break
        logger.info("Próxima sincronización en %.1f horas", intervalo_horas)
        time.sleep(intervalo_horas * 3600)


if __name__ == "__main__":
    main()
