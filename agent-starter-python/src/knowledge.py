"""Búsqueda en la base de conocimiento de la UAM.

El índice lo genera el servicio knowledge-sync (knowledge-sync/sync.py): una base
SQLite con la tabla FTS5 ``fragmentos`` (titulo, texto, fuente, categoria, url,
privado) que se reemplaza de forma atómica en cada sincronización.
"""

from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path

KNOWLEDGE_DB = os.getenv("KNOWLEDGE_DB", "/data/knowledge.db")

# Palabras sin valor de búsqueda (ya sin tildes). Incluye el nombre de la
# universidad porque aparece en casi todos los documentos.
PALABRAS_VACIAS = frozenset(
    [
        "al",
        "algo",
        "alguna",
        "alguno",
        "ante",
        "antes",
        "cada",
        "como",
        "con",
        "cual",
        "cuales",
        "cuando",
        "del",
        "desde",
        "dime",
        "donde",
        "ella",
        "ellos",
        "entre",
        "era",
        "eres",
        "esa",
        "ese",
        "eso",
        "esta",
        "estan",
        "este",
        "esto",
        "estos",
        "favor",
        "hay",
        "las",
        "les",
        "los",
        "mas",
        "mis",
        "muy",
        "nos",
        "para",
        "pero",
        "por",
        "porque",
        "puedo",
        "puede",
        "que",
        "quien",
        "quiero",
        "saber",
        "ser",
        "sin",
        "sobre",
        "sus",
        "tambien",
        "tengo",
        "tiene",
        "una",
        "uno",
        "unos",
        "usted",
        "universidad",
        "uam",
        "autonoma",
        "manizales",
    ]
)


class IndiceNoDisponibleError(RuntimeError):
    """El índice aún no existe: primera sincronización en curso o servicio detenido."""


@dataclass
class Resultado:
    titulo: str
    texto: str
    fuente: str
    categoria: str
    url: str
    privado: bool


def _sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def construir_consulta(pregunta: str) -> str | None:
    """Convierte una pregunta hablada en una consulta FTS5 tolerante a plurales."""
    terminos: list[str] = []
    for palabra in re.findall(r"\w+", _sin_tildes(pregunta.lower())):
        if palabra in PALABRAS_VACIAS or (len(palabra) < 3 and not palabra.isdigit()):
            continue
        # Prefijo en vez de palabra completa: "carreras" -> "carrer*" encuentra "carrera".
        raiz = palabra[:-2] if len(palabra) > 5 else palabra
        if raiz not in terminos:
            terminos.append(raiz)
    if not terminos:
        return None
    return " OR ".join(f'"{termino}"*' for termino in terminos)


def buscar(
    pregunta: str, limite: int = 3, ruta_db: str | Path | None = None
) -> list[Resultado]:
    """Devuelve los mejores fragmentos, como máximo uno por documento."""
    ruta = Path(ruta_db or KNOWLEDGE_DB).resolve()
    if not ruta.is_file():
        raise IndiceNoDisponibleError(str(ruta))

    consulta = construir_consulta(pregunta)
    if consulta is None:
        return []

    conexion = sqlite3.connect(f"{ruta.as_uri()}?mode=ro", uri=True)
    try:
        filas = conexion.execute(
            "SELECT titulo, texto, fuente, categoria, url, privado FROM fragmentos"
            " WHERE fragmentos MATCH ? ORDER BY bm25(fragmentos, 4.0, 1.0) LIMIT ?",
            (consulta, limite * 5),
        ).fetchall()
    finally:
        conexion.close()

    resultados: list[Resultado] = []
    vistos: set[str] = set()
    for titulo, texto, fuente, categoria, url, privado in filas:
        if titulo in vistos:
            continue
        vistos.add(titulo)
        resultados.append(
            Resultado(titulo, texto, fuente, categoria, url, bool(int(privado)))
        )
        if len(resultados) == limite:
            break
    return resultados


def formatear_resultados(resultados: list[Resultado], max_caracteres: int = 700) -> str:
    """Texto breve para el LLM: fuente, título y el fragmento relevante."""
    if not resultados:
        return (
            "No se encontró información sobre eso en los documentos oficiales ni en el"
            " Portal de Conocimiento de la UAM. Dilo con honestidad, no inventes datos"
            " y sugiere contactar directamente a la universidad."
        )

    partes = []
    for numero, resultado in enumerate(resultados, start=1):
        detalle = f", {resultado.categoria}" if resultado.categoria else ""
        encabezado = (
            f'Fuente {numero}: "{resultado.titulo}" ({resultado.fuente}{detalle}).'
        )
        if resultado.privado:
            partes.append(
                f"{encabezado} Es una guía privada: su contenido requiere iniciar sesión"
                f" con la Cuenta UAM en {resultado.url}"
            )
        elif not resultado.texto:
            partes.append(
                f"{encabezado} Solo está disponible el título; enlace: {resultado.url}"
            )
        else:
            texto = resultado.texto
            if len(texto) > max_caracteres:
                texto = texto[:max_caracteres].rsplit(" ", 1)[0] + "..."
            partes.append(f"{encabezado} {texto}")
    return "\n".join(partes)
