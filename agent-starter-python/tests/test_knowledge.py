import sqlite3

import pytest

import knowledge
from agent import ElianAgent

# Mismo esquema que knowledge-sync/sync.py
ESQUEMA = """
CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE VIRTUAL TABLE fragmentos USING fts5(
    titulo, texto, fuente UNINDEXED, categoria UNINDEXED, url UNINDEXED,
    privado UNINDEXED, tokenize = 'unicode61 remove_diacritics 2'
);
"""


@pytest.fixture
def indice(tmp_path):
    ruta = tmp_path / "knowledge.db"
    conexion = sqlite3.connect(ruta)
    conexion.executescript(ESQUEMA)
    conexion.executemany(
        "INSERT INTO fragmentos VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                "Acuerdo No. 001 Reglamento General Estudiantil",
                "La matrícula académica se formaliza con el pago de los derechos"
                " pecuniarios dentro de las fechas del calendario académico.",
                "Documentos UAM",
                "Normatividad - Consejo Superior",
                "https://www.autonoma.edu.co/conoce-la-uam/documentos-uam",
                0,
            ),
            (
                "¿Cómo realizar la postulación a grado?",
                "",
                "Portal de Conocimiento",
                "*FAQ, Estudiantes",
                "https://portalconocimiento.autonoma.edu.co/postulacion-grado/",
                1,
            ),
            (
                "Depuración correo Gmail",
                "Para liberar espacio en el correo institucional elimina adjuntos"
                " grandes.",
                "Portal de Conocimiento",
                "*FAQ, Gmail (Correo)",
                "https://portalconocimiento.autonoma.edu.co/depuracion-correo-gmail/",
                0,
            ),
        ],
    )
    conexion.commit()
    conexion.close()
    return ruta


def test_construir_consulta_quita_palabras_vacias_tildes_y_plurales():
    consulta = knowledge.construir_consulta("¿Cómo hago las matrículas en la UAM?")

    assert '"matricul"*' in consulta
    assert "uam" not in consulta
    assert "como" not in consulta
    assert knowledge.construir_consulta("¿qué es eso?") is None


def test_buscar_encuentra_documento_sin_tildes_ni_plural(indice):
    resultados = knowledge.buscar("matriculas", ruta_db=indice)

    assert resultados[0].titulo == "Acuerdo No. 001 Reglamento General Estudiantil"
    assert resultados[0].privado is False


def test_buscar_sin_indice_lanza_error(tmp_path):
    with pytest.raises(knowledge.IndiceNoDisponibleError):
        knowledge.buscar("grado", ruta_db=tmp_path / "no-existe.db")


def test_formatear_entrada_privada_remite_al_portal(indice):
    texto = knowledge.formatear_resultados(
        knowledge.buscar("postulacion a grado", ruta_db=indice)
    )

    assert "Cuenta UAM" in texto
    assert "portalconocimiento.autonoma.edu.co/postulacion-grado/" in texto


def test_formatear_sin_resultados_pide_no_inventar():
    assert "no inventes" in knowledge.formatear_resultados([])


def test_elian_expone_herramienta_de_busqueda():
    herramientas = [tool.info.name for tool in ElianAgent()._tools]
    assert "buscar_informacion_uam" in herramientas


async def test_elian_busca_en_la_base_de_conocimiento(indice, monkeypatch):
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DB", str(indice))

    respuesta = await ElianAgent().buscar_informacion_uam(
        context=None, consulta="espacio en el correo gmail"
    )

    assert "Depuración correo Gmail" in respuesta


async def test_elian_informa_si_el_indice_no_esta_listo(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DB", str(tmp_path / "pendiente.db"))

    respuesta = await ElianAgent().buscar_informacion_uam(
        context=None, consulta="grado"
    )

    assert "sincroniz" in respuesta
