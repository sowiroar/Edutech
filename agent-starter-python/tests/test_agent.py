import pytest
from livekit.agents import ChatContext

from agent import ElianAgent, LiraAgent, NexusAgent, get_tts_engine


def test_agent_voices_and_initialization():
    """Verifica que cada agente se inicialice con su personalidad y voz correspondiente."""
    lira = LiraAgent()
    nexus = NexusAgent()
    elian = ElianAgent()

    assert "Lira" in lira.instructions
    assert "ef_dora" in lira.tts._opts.voice

    assert "Nexus" in nexus.instructions
    assert "em_alex" in nexus.tts._opts.voice

    assert "Elian" in elian.instructions
    assert "em_santa" in elian.tts._opts.voice


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
    chat_ctx.add_message(role="user", content="Hola, ¿cómo implemento un modelo YOLO en PyTorch?")

    lira = LiraAgent(chat_ctx=chat_ctx)
    nexus_target, message = await lira.transfer_to_nexus(context=None)

    assert isinstance(nexus_target, NexusAgent)
    assert "Nexus" in message
    assert nexus_target.chat_ctx is not None
    assert len(nexus_target.chat_ctx.items) == 1
    assert "YOLO" in nexus_target.chat_ctx.items[0].text_content


@pytest.mark.asyncio
async def test_lira_transfer_to_elian_execution():
    """Verifica la ejecución de la herramienta de transferencia de Lira hacia Elian."""
    chat_ctx = ChatContext()
    chat_ctx.add_message(role="user", content="¿Cuáles son los requisitos de admisión en la Universidad Autónoma de Manizales?")

    lira = LiraAgent(chat_ctx=chat_ctx)
    elian_target, message = await lira.transfer_to_elian(context=None)

    assert isinstance(elian_target, ElianAgent)
    assert "Elian" in message
    assert elian_target.chat_ctx is not None
    assert len(elian_target.chat_ctx.items) == 1
    assert "Universidad Autónoma de Manizales" in elian_target.chat_ctx.items[0].text_content

