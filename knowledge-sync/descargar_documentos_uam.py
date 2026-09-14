#!/usr/bin/env python3
"""Descarga incrementalmente los documentos publicados en Documentos UAM.

Dependencias:
    python -m pip install requests beautifulsoup4

Ejemplo:
    python descargar_documentos_uam.py --directorio documentos_uam

Uso desde otro script:
    from descargar_documentos_uam import descargar_documentos

    resumen = descargar_documentos(
        "https://www.autonoma.edu.co/conoce-la-uam/documentos-uam",
        "documentos_uam",
        "documentos_uam/documentos_uam.csv",
    )
"""

from __future__ import annotations

import argparse
import csv
import mimetypes
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Iterator
from urllib.parse import unquote, urljoin, urlparse

if TYPE_CHECKING:
    import requests
    from bs4 import BeautifulSoup, Tag


URL_INICIAL = "https://www.autonoma.edu.co/conoce-la-uam/documentos-uam"
__all__ = ["descargar_documentos"]
CAMPOS_CSV = [
    "titulo",
    "grupo_de_interes",
    "origen",
    "categoria",
    "nombre_archivo",
]
EXTENSIONES_DOCUMENTO = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".zip", ".rar", ".7z", ".txt", ".csv",
}


def cargar_dependencias() -> None:
    """Carga librerías externas después de procesar --help y los argumentos."""
    global requests, BeautifulSoup, Tag, HTTPAdapter, Retry
    try:
        import requests
        from bs4 import BeautifulSoup, Tag
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Falta una dependencia. Instálela con: "
            "python -m pip install requests beautifulsoup4"
        ) from exc


def texto(elemento: Tag | None) -> str:
    return " ".join(elemento.stripped_strings) if elemento else ""


def clave(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip().casefold()


def nombre_seguro(nombre: str) -> str:
    nombre = unicodedata.normalize("NFKC", unquote(nombre))
    nombre = Path(nombre).name
    nombre = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nombre)
    nombre = re.sub(r"\s+", " ", nombre).strip(" .")
    return nombre[:220] or "documento"


def crear_sesion() -> requests.Session:
    reintentos = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        respect_retry_after_header=True,
    )
    sesion = requests.Session()
    sesion.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
        ),
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.7",
    })
    sesion.mount("https://", HTTPAdapter(max_retries=reintentos))
    sesion.mount("http://", HTTPAdapter(max_retries=reintentos))
    return sesion


def obtener(sesion: requests.Session, url: str, timeout: int) -> requests.Response:
    respuesta = sesion.get(url, timeout=timeout)
    respuesta.raise_for_status()
    return respuesta


def buscar_tabla(soup: BeautifulSoup) -> Tag:
    # La vista de Drupal utiliza normalmente views-table. Se conserva un
    # fallback basado en los encabezados para tolerar cambios menores de tema.
    tabla = soup.select_one("table.views-table")
    if tabla:
        return tabla
    for candidata in soup.find_all("table"):
        encabezados = [clave(texto(th)) for th in candidata.find_all("th")]
        if encabezados and "titulo" in encabezados and "origen" in encabezados:
            return candidata
    raise RuntimeError("No se encontró la tabla de documentos en la página.")


def leer_filas(soup: BeautifulSoup, url_pagina: str) -> list[dict[str, str]]:
    tabla = buscar_tabla(soup)
    filas: list[dict[str, str]] = []
    cuerpo = tabla.find("tbody") or tabla
    for tr in cuerpo.find_all("tr", recursive=False):
        celdas = tr.find_all("td", recursive=False)
        if len(celdas) < 4:
            continue
        enlace = celdas[0].find("a", href=True)
        if not enlace:
            continue
        filas.append({
            "titulo": texto(celdas[0]),
            "grupo_de_interes": texto(celdas[1]),
            "origen": texto(celdas[2]),
            "categoria": texto(celdas[3]),
            "url_detalle": urljoin(url_pagina, enlace["href"]),
        })
    return filas


def siguiente_pagina(soup: BeautifulSoup, url_actual: str) -> str | None:
    selectores = (
        "li.pager__item--next a[href]",
        "li.pager-next a[href]",
        "a[rel='next'][href]",
    )
    for selector in selectores:
        enlace = soup.select_one(selector)
        if enlace:
            return urljoin(url_actual, enlace["href"])
    return None


def recorrer_paginas(
    sesion: requests.Session, url_inicial: str, timeout: int, pausa: float
) -> Iterator[tuple[int, dict[str, str]]]:
    url: str | None = url_inicial
    visitadas: set[str] = set()
    numero = 1
    while url and url not in visitadas:
        visitadas.add(url)
        print(f"Leyendo página {numero}: {url}")
        respuesta = obtener(sesion, url, timeout)
        soup = BeautifulSoup(respuesta.text, "html.parser")
        for fila in leer_filas(soup, respuesta.url):
            yield numero, fila
        url = siguiente_pagina(soup, respuesta.url)
        numero += 1
        if url and pausa:
            time.sleep(pausa)


def es_enlace_descarga(enlace: Tag) -> bool:
    href = enlace.get("href", "")
    ruta = urlparse(href).path.lower()
    etiqueta = clave(texto(enlace))
    return (
        Path(ruta).suffix in EXTENSIONES_DOCUMENTO
        or "descargar" in etiqueta
        or enlace.has_attr("download")
    )


def obtener_url_documento(
    sesion: requests.Session, url_detalle: str, timeout: int
) -> str:
    respuesta = obtener(sesion, url_detalle, timeout)
    soup = BeautifulSoup(respuesta.text, "html.parser")
    candidatos = [a for a in soup.find_all("a", href=True) if es_enlace_descarga(a)]
    if not candidatos:
        raise RuntimeError("La ficha no contiene un enlace de descarga reconocible.")
    # Prioriza enlaces cuyo destino ya tiene extensión de documento.
    candidatos.sort(
        key=lambda a: Path(urlparse(a["href"]).path.lower()).suffix
        not in EXTENSIONES_DOCUMENTO
    )
    return urljoin(respuesta.url, candidatos[0]["href"])


def nombre_desde_respuesta(respuesta: requests.Response, url: str) -> str:
    disposicion = respuesta.headers.get("Content-Disposition", "")
    coincidencia = re.search(
        r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)",
        disposicion,
        flags=re.IGNORECASE,
    )
    bruto = next((g for g in coincidencia.groups() if g), "") if coincidencia else ""
    bruto = bruto or Path(urlparse(url).path).name
    nombre = nombre_seguro(bruto)
    if not Path(nombre).suffix:
        tipo = respuesta.headers.get("Content-Type", "").split(";", 1)[0]
        nombre += mimetypes.guess_extension(tipo) or ".bin"
    return nombre


def descargar_archivo(
    sesion: requests.Session,
    url: str,
    directorio: Path,
    timeout: int,
) -> tuple[str, bool]:
    with obtener(sesion, url, timeout) as respuesta:
        nombre = nombre_desde_respuesta(respuesta, respuesta.url)
        destino = directorio / nombre
        if destino.is_file() and destino.stat().st_size > 0:
            return nombre, False

        # No se reemplaza otro documento con el mismo nombre.
        if destino.exists():
            base, extension = destino.stem, destino.suffix
            indice = 2
            while destino.exists():
                destino = directorio / f"{base}_{indice}{extension}"
                indice += 1
            nombre = destino.name

        temporal = destino.with_name(destino.name + ".part")
        try:
            with temporal.open("wb") as archivo:
                for bloque in respuesta.iter_content(chunk_size=1024 * 128):
                    if bloque:
                        archivo.write(bloque)
            if temporal.stat().st_size == 0:
                raise RuntimeError("El servidor devolvió un archivo vacío.")
            temporal.replace(destino)
        except Exception:
            temporal.unlink(missing_ok=True)
            raise
    return nombre, True


def leer_registro(ruta_csv: Path) -> tuple[set[str], set[str]]:
    titulos: set[str] = set()
    archivos: set[str] = set()
    if not ruta_csv.exists():
        return titulos, archivos
    with ruta_csv.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames and not set(CAMPOS_CSV).issubset(lector.fieldnames):
            raise RuntimeError(
                f"El CSV existente no contiene las columnas requeridas: {CAMPOS_CSV}"
            )
        for fila in lector:
            if fila.get("titulo"):
                titulos.add(clave(fila["titulo"]))
            if fila.get("nombre_archivo"):
                archivos.add(fila["nombre_archivo"].casefold())
    return titulos, archivos


def abrir_escritor(ruta_csv: Path) -> tuple[object, csv.DictWriter]:
    nuevo = not ruta_csv.exists() or ruta_csv.stat().st_size == 0
    archivo = ruta_csv.open("a", encoding="utf-8-sig" if nuevo else "utf-8", newline="")
    escritor = csv.DictWriter(archivo, fieldnames=CAMPOS_CSV)
    if nuevo:
        escritor.writeheader()
        archivo.flush()
    return archivo, escritor


def descargar_documentos(
    url: str,
    directorio: str | Path,
    ruta_csv: str | Path,
    *,
    timeout: int = 60,
    pausa: float = 0.4,
) -> dict[str, int | str]:
    """Descarga los documentos y actualiza el CSV de forma incremental.

    Esta es la interfaz pública del módulo. Puede importarse así::

        from descargar_documentos_uam import descargar_documentos

        resumen = descargar_documentos(
            "https://www.autonoma.edu.co/conoce-la-uam/documentos-uam",
            "./documentos",
            "./documentos/documentos_uam.csv",
        )

    Args:
        url: URL de la página que contiene la tabla paginada.
        directorio: Directorio donde se guardarán los documentos.
        ruta_csv: Ruta del archivo CSV que se creará o actualizará.
        timeout: Tiempo máximo de cada petición HTTP, en segundos.
        pausa: Pausa entre peticiones, en segundos.

    Returns:
        Diccionario con ``nuevos``, ``omitidos``, ``errores`` y ``ruta_csv``.

    Raises:
        RuntimeError: Si faltan dependencias, el CSV no es compatible o no se
            puede reconocer la tabla principal.
        requests.RequestException: Si falla la consulta de la página principal.
    """
    cargar_dependencias()
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url debe ser una cadena no vacía.")
    if timeout <= 0:
        raise ValueError("timeout debe ser mayor que cero.")
    if pausa < 0:
        raise ValueError("pausa no puede ser negativa.")

    directorio = Path(directorio).expanduser().resolve()
    directorio.mkdir(parents=True, exist_ok=True)
    ruta_csv = Path(ruta_csv).expanduser().resolve()
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)

    titulos_csv, archivos_csv = leer_registro(ruta_csv)
    sesion = crear_sesion()
    nuevos = omitidos = errores = 0

    archivo_csv, escritor = abrir_escritor(ruta_csv)
    try:
        for pagina, fila in recorrer_paginas(
            sesion, url, timeout, pausa
        ):
            titulo_id = clave(fila["titulo"])
            if titulo_id in titulos_csv:
                print(f"  OMITIDO (ya registrado): {fila['titulo']}")
                omitidos += 1
                continue
            try:
                url_documento = obtener_url_documento(
                    sesion, fila["url_detalle"], timeout
                )
                nombre, fue_descargado = descargar_archivo(
                    sesion, url_documento, directorio, timeout
                )
                # Si está físicamente y no figuraba en el CSV, se registra sin bajarlo.
                registro = {campo: fila.get(campo, "") for campo in CAMPOS_CSV}
                registro["nombre_archivo"] = nombre
                escritor.writerow(registro)
                archivo_csv.flush()
                titulos_csv.add(titulo_id)
                archivos_csv.add(nombre.casefold())
                nuevos += 1
                accion = "DESCARGADO" if fue_descargado else "REGISTRADO (ya existía)"
                print(f"  {accion}: {nombre}")
                if pausa:
                    time.sleep(pausa)
            except Exception as exc:
                errores += 1
                print(
                    f"  ERROR en página {pagina}, {fila['titulo']}: {exc}",
                    file=sys.stderr,
                )
    finally:
        archivo_csv.close()
        sesion.close()

    print(
        f"Finalizado: {nuevos} nuevos/registrados, {omitidos} omitidos, "
        f"{errores} errores. CSV: {ruta_csv}"
    )
    return {
        "nuevos": nuevos,
        "omitidos": omitidos,
        "errores": errores,
        "ruta_csv": str(ruta_csv),
    }


def ejecutar(args: argparse.Namespace) -> int:
    ruta_csv = args.csv or args.directorio / "documentos_uam.csv"
    resumen = descargar_documentos(
        args.url,
        args.directorio,
        ruta_csv,
        timeout=args.timeout,
        pausa=args.pausa,
    )
    return 1 if resumen["errores"] else 0


class AnalizadorArgumentos(argparse.ArgumentParser):
    """Muestra la ayuda completa antes de informar un uso incorrecto."""

    def error(self, message: str) -> None:
        self.print_help(sys.stderr)
        self.exit(2, f"\nError: {message}\n")


def argumentos() -> argparse.Namespace:
    parser = AnalizadorArgumentos(
        description=(
            "Descarga incrementalmente todos los documentos publicados en la "
            "página Documentos UAM y genera un registro CSV."
        ),
        epilog="""
Ejemplos:
  %(prog)s
  %(prog)s --directorio documentos_uam
  %(prog)s --directorio ./documentos --csv ./registro.csv
  %(prog)s --pausa 1.0 --timeout 120

Uso desde otro script:
  from descargar_documentos_uam import descargar_documentos

  resumen = descargar_documentos(
      "https://www.autonoma.edu.co/conoce-la-uam/documentos-uam",
      "./documentos",
      "./documentos/documentos_uam.csv",
  )

Comportamiento incremental:
  * Si un documento ya aparece en el CSV, se omite.
  * Si el archivo ya existe en el directorio pero no está en el CSV, se
    registra sin descargarlo de nuevo.
  * El CSV se actualiza después de cada documento, por lo que el proceso puede
    interrumpirse y reanudarse sin perder el progreso guardado.

Dependencias:
  python -m pip install requests beautifulsoup4
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", default=URL_INICIAL, help="URL inicial del listado")
    parser.add_argument(
        "--directorio", type=Path, default=Path("documentos_uam"),
        help="Directorio de descarga (predeterminado: documentos_uam)",
    )
    parser.add_argument(
        "--csv", type=Path, default=None,
        help="Ruta del CSV (predeterminado: <directorio>/documentos_uam.csv)",
    )
    parser.add_argument(
        "--timeout", type=int, default=60,
        help="tiempo máximo por petición, en segundos (predeterminado: 60)",
    )
    parser.add_argument(
        "--pausa", type=float, default=0.4,
        help="Pausa en segundos entre peticiones (predeterminado: 0.4)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        raise SystemExit(ejecutar(argumentos()))
    except KeyboardInterrupt:
        print("\nInterrumpido. El progreso ya guardado se conservará.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
