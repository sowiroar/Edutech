import sqlite3

import pymupdf
import pytest

import sync
from sync import Registro


def test_html_a_texto_decodifica_entidades_y_quita_etiquetas():
    contenido = "<p>Cambio &amp; <b>ALMERA</b></p>\n<p>paso 1</p>"
    assert sync.html_a_texto(contenido) == "Cambio & ALMERA paso 1"


def test_fragmentar_con_solape_cubre_todo_el_texto():
    texto = " ".join(f"p{i}" for i in range(400))
    fragmentos = sync.fragmentar(texto, palabras=180, solape=40)

    assert fragmentos[0].split()[0] == "p0"
    assert fragmentos[1].split()[0] == "p140"
    assert fragmentos[-1].split()[-1] == "p399"
    assert sync.fragmentar("   ") == []


def test_extraer_texto_pdf(tmp_path):
    ruta = tmp_path / "reglamento.pdf"
    with pymupdf.open() as documento:
        documento.new_page().insert_text((72, 72), "Reglamento General Estudiantil")
        documento.save(ruta)

    assert "Reglamento General Estudiantil" in sync.extraer_texto_pdf(ruta)


def test_extraer_texto_pdf_invalido_devuelve_vacio(tmp_path):
    ruta = tmp_path / "roto.pdf"
    ruta.write_bytes(b"no es un pdf")
    assert sync.extraer_texto_pdf(ruta) == ""


def test_registro_desde_post_publico():
    post = {
        "title": {"rendered": "Inscripci&oacute;n materias"},
        "content": {"rendered": "<p>Ingresa a <strong>IntraUAM</strong></p>"},
        "link": "https://portalconocimiento.autonoma.edu.co/inscripcion/",
        "_embedded": {
            "wp:term": [
                [{"name": "*FAQ"}, {"name": "Estudiantes"}],
                [{"name": "Estudiantes"}],
            ]
        },
    }
    registro = sync.registro_desde_post(post)

    assert registro.titulo == "Inscripción materias"
    assert registro.texto == "Ingresa a IntraUAM"
    assert registro.categoria == "*FAQ, Estudiantes"
    assert registro.privado is False


def test_registro_desde_post_privado_no_indexa_aviso():
    post = {
        "title": {"rendered": "Archivar una PQRSF"},
        "content": {
            "rendered": (
                '<div class="members-access-error">'
                "Lo sentimos, esta publicación es privada.</div>"
            )
        },
        "link": "https://portalconocimiento.autonoma.edu.co/archivar-pqrsf/",
    }
    registro = sync.registro_desde_post(post)

    assert registro.privado is True
    assert registro.texto == ""


def test_construir_indice_busca_sin_tildes_y_publica_atomicamente(tmp_path):
    registros = [
        Registro(
            "Documentos UAM",
            "Reglamento General Estudiantil",
            "La matrícula académica se realiza cada semestre " * 30,
            "Normatividad",
        ),
        Registro(
            "Portal de Conocimiento",
            "Postulación a grado",
            "",
            url="https://p/grado",
            privado=True,
        ),
    ]
    ruta = tmp_path / "knowledge.db"

    assert sync.construir_indice(registros, ruta) == 3
    assert not ruta.with_suffix(".tmp").exists()

    conexion = sqlite3.connect(ruta)
    titulos = conexion.execute(
        "SELECT titulo FROM fragmentos WHERE fragmentos MATCH ?", ("matricula",)
    ).fetchall()
    privado = conexion.execute(
        "SELECT privado FROM fragmentos WHERE fragmentos MATCH ?", ("postulacion",)
    ).fetchone()
    registros_meta = conexion.execute(
        "SELECT valor FROM meta WHERE clave = 'registros'"
    ).fetchone()
    conexion.close()

    assert titulos[0][0] == "Reglamento General Estudiantil"
    assert privado[0] == 1
    assert registros_meta[0] == "2"


def test_sincronizar_conserva_indice_anterior_si_falla_una_fuente(
    tmp_path, monkeypatch
):
    ruta = tmp_path / "knowledge.db"
    ruta.write_bytes(b"indice-anterior")

    def falla(*_args, **_kwargs):
        raise RuntimeError("sitio caido")

    monkeypatch.setattr(sync, "leer_documentos_uam", falla)

    assert sync.sincronizar(tmp_path, None) is False
    assert ruta.read_bytes() == b"indice-anterior"


def test_sincronizar_combina_fuentes(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sync,
        "leer_documentos_uam",
        lambda *_a, **_k: [
            Registro("Documentos UAM", "Acuerdo 006", "educacion inclusiva")
        ],
    )
    monkeypatch.setattr(
        sync,
        "leer_portal_conocimiento",
        lambda *_a, **_k: [
            Registro("Portal de Conocimiento", "Gmail", "depuracion de correo")
        ],
    )

    assert sync.sincronizar(tmp_path, ("https://p", "usuario", "clave")) is True

    conexion = sqlite3.connect(tmp_path / "knowledge.db")
    fuentes = {fila[0] for fila in conexion.execute("SELECT fuente FROM fragmentos")}
    conexion.close()
    assert fuentes == {"Documentos UAM", "Portal de Conocimiento"}


@pytest.mark.parametrize("valor", ["0", "-1"])
def test_main_con_intervalo_no_positivo_sincroniza_una_vez(
    tmp_path, monkeypatch, valor
):
    llamadas = []
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SYNC_INTERVAL_HOURS", valor)
    monkeypatch.delenv("PORTAL_CONOCIMIENTO_USER", raising=False)
    monkeypatch.setattr(sync, "sincronizar", lambda *args: llamadas.append(args))

    sync.main()

    assert llamadas == [(tmp_path, None)]
