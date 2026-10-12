import pytest
from livekit.agents import ChatContext

from agent import ElianAgent, LiraAgent, NexusAgent


def test_agent_voices_and_initialization():
    """Verifica que cada agente se inicialice con su personalidad y voz correspondiente de Gemini Live."""
    lira = LiraAgent()
    nexus = NexusAgent()
    elian = ElianAgent()

    assert "Lira" in lira.instructions
    assert lira.llm._opts.voice == "Aoede"

    assert "Nexus" in nexus.instructions
    assert nexus.llm._opts.voice == "Puck"

    assert "Elian" in elian.instructions
    # Kore (femenina), no Charon: cambiada el 2026-10-09 al integrar el
    # personaje visual ELIAN de la Familia VIVA, que es femenino.
    assert elian.llm._opts.voice == "Kore"


def test_agent_avatar_character_mapping():
    """Verifica el personaje de la Familia VIVA (Fase 2) asociado a cada
    agente: Lira->LIRA y Elian->ELIAN coinciden por nombre; Nexus->NEXO
    (no ATLAS) porque NEXO es el único con animación de habla verificada
    (ver Avatar/FAMILIA_VIVA.md)."""
    assert LiraAgent().AVATAR_CHARACTER == "LIRA"
    assert NexusAgent().AVATAR_CHARACTER == "NEXO"
    assert ElianAgent().AVATAR_CHARACTER == "ELIAN"


@pytest.mark.asyncio
async def test_anunciar_personaje_avatar_is_a_safe_noop_without_a_session():
    """Fuera de una sesión real (como en estas pruebas), self.session no
    existe: anunciar_personaje_avatar debe tragarse eso sin lanzar, igual
    que ya hace emitir_datos_frontend."""
    lira = LiraAgent()
    await lira.anunciar_personaje_avatar()  # no debe lanzar excepción


def test_lira_handoff_tools_registered():
    """Verifica que Lira exponga las herramientas de enrutamiento a Nexus y Elian."""
    lira = LiraAgent()
    tool_names = [tool.info.name for tool in lira._tools]

    assert "transfer_to_nexus" in tool_names
    assert "transfer_to_elian" in tool_names


def test_specialists_cross_handoff_tools():
    """Verifica que Nexus y Elian puedan referenciar cruzadamente sus temas."""
    nexus = NexusAgent()
    elian = ElianAgent()

    nexus_tools = [tool.info.name for tool in nexus._tools]
    elian_tools = [tool.info.name for tool in elian._tools]

    assert "transfer_to_elian" in nexus_tools
    assert "transfer_to_nexus" in elian_tools


@pytest.mark.asyncio
async def test_lira_transfer_to_nexus_execution():
    """Verifica la ejecución de la herramienta de transferencia de Lira hacia Nexus."""
    chat_ctx = ChatContext()
    chat_ctx.add_message(
        role="user", content="Hola, ¿cómo implemento un modelo YOLO en PyTorch?"
    )

    lira = LiraAgent(chat_ctx=chat_ctx)
    nexus_target = await lira.transfer_to_nexus(context=None)

    assert isinstance(nexus_target, NexusAgent)
    assert nexus_target.chat_ctx is not None
    assert len(nexus_target.chat_ctx.items) == 1
    assert "YOLO" in nexus_target.chat_ctx.items[0].text_content


@pytest.mark.asyncio
async def test_lira_transfer_to_elian_execution():
    """Verifica la ejecución de la herramienta de transferencia de Lira hacia Elian."""
    chat_ctx = ChatContext()
    chat_ctx.add_message(
        role="user",
        content="¿Cuáles son los requisitos de admisión en la Universidad Autónoma de Manizales?",
    )

    lira = LiraAgent(chat_ctx=chat_ctx)
    elian_target = await lira.transfer_to_elian(context=None)

    assert isinstance(elian_target, ElianAgent)
    assert elian_target.chat_ctx is not None
    assert len(elian_target.chat_ctx.items) == 1
    assert (
        "Universidad Autónoma de Manizales"
        in elian_target.chat_ctx.items[0].text_content
    )


@pytest.mark.asyncio
async def test_base_agent_on_user_turn_completed():
    """Verifica que on_user_turn_completed se ejecute de forma segura sin excepciones."""
    from livekit.agents import llm
    nexus = NexusAgent()
    turn_ctx = llm.ChatContext()
    message = llm.ChatMessage(role="user", content=["Hola, mi nombre es Daniel y estudio Ingeniería de Sistemas."])

    # Debe ejecutarse sin lanzar excepciones
    await nexus.on_user_turn_completed(turn_ctx, message)
    assert "Daniel" in message.text_content


@pytest.mark.asyncio
async def test_elian_buscar_informacion_uam_fallback(monkeypatch):
    """Verifica que buscar_informacion_uam devuelva un mensaje coherente ante cualquier consulta."""
    monkeypatch.setenv("GOOGLE_API_KEY", "mock-key-for-tests")
    elian = ElianAgent()
    respuesta = await elian.buscar_informacion_uam(None, "requisitos de matricula")
    assert isinstance(respuesta, str)
    assert len(respuesta) > 0


@pytest.mark.asyncio
async def test_nexus_consultas_especializacion_ia_tool():
    """Verifica el registro y ejecución de consultas_especializacion_ia en NexusAgent."""
    nexus = NexusAgent()
    tool_names = [tool.info.name for tool in nexus._tools]
    assert "consultas_especializacion_ia" in tool_names
    assert "listar_documentos_especializacion_ia" in tool_names

    catalogo = await nexus.listar_documentos_especializacion_ia(None)
    assert isinstance(catalogo, str)
    assert "documentos disponibles" in catalogo or "especialización" in catalogo
