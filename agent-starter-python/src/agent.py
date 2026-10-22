from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import textwrap
from typing import Any

from dotenv import load_dotenv
from google.genai import types as genai_types
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    JobContext,
    JobProcess,
    RunContext,
    TurnHandlingOptions,
    cli,
    function_tool,
    llm,
)
from livekit.plugins import google

import knowledge
import memory_manager
import rag_llamaindex
import rag_nexus
import viva_telemetry
from background_tasks import spawn_background

logger = logging.getLogger("agent-multi")

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Configuración de Google Gemini Live API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")

# Prefetch de memoria Mem0.
#
# Version anterior (2026-09-29): disparaba la busqueda solo con la
# transcripcion FINAL, asumiendo que el endpointing dinamico (0.5-3s de
# silencio) dejaba un hueco antes de que el turno se cerrara. Auditoria del
# 2026-09-30 encontro que esa suposicion era falsa para este pipeline: Gemini
# Live usa deteccion de turno del lado del servidor y esta libreria IGNORA
# por completo nuestro turn_detection/endpointing (log real, repetido en
# produccion: "turn_detection is a TurnDetector, but the LLM is a
# RealtimeModel with server-side turn detection enabled, ignoring the
# turn_detection setting"). Ademas, la transcripcion final y el cierre del
# turno salen de la MISMA señal de Gemini (turn_complete), asi que casi no
# hay hueco real que aprovechar ahi.
#
# Lo que si existe: Gemini manda la transcripcion en fragmentos progresivos
# MIENTRAS el usuario habla (is_final=False), no solo al terminar. Ahora se
# dispara con el PRIMER fragmento de cada turno (identificado por item_id,
# no por el texto — el texto final nunca es igual al de un fragmento
# parcial), lo que da una ventana real: todo lo que dura el resto del
# enunciado del usuario, en vez de milisegundos.
#
# Una entrada por user_id: (item_id, tarea). Se consume y descarta en
# on_user_turn_completed, emparejando por new_message.id (mismo item_id que
# usa el plugin de Gemini al crear el ChatMessage) en vez de por texto
# (Claude, 2026-09-30).
_memoria_prefetch: dict[str, tuple[str | None, asyncio.Task]] = {}


def _resolver_user_id(session) -> str:
    return viva_telemetry.memory_identity(session)


def get_realtime_model(voice: str = "Aoede") -> google.realtime.RealtimeModel:
    """Instancia del motor Gemini Live API (RealtimeModel).
    Voces soportadas:
    - Aoede: Femenina natural y relajada en español/inglés (Lira - Recepción y Triage).
    - Puck: Masculina dinámica, alegre y técnica (Nexus - Especialista en IA).
    - Kore: Femenina formal, calmada y profesional (Elian - Especialista UAM).
      Antes era Charon (masculina): se cambió el 2026-10-09 al integrar el
      personaje visual ELIAN de la Familia VIVA, que es femenino — Charon
      no calzaba con el avatar. Verificado en vivo que Kore conecta
      correctamente con la API real antes de este cambio.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY or "mock-key-for-tests"
    model = os.getenv("GEMINI_LIVE_MODEL") or GEMINI_LIVE_MODEL or "gemini-3.8-live"
    return google.realtime.RealtimeModel(
        model=model,
        voice=voice,
        api_key=api_key,
        temperature=0.7,
        # Gemini Live detecta el inicio/fin de turno del lado del servidor y
        # (confirmado por auditoria del 2026-09-30) ignora por completo
        # nuestro turn_detection/VAD local, asi que la unica perilla real
        # para "detecta voz donde no hay" es esta. START_SENSITIVITY_LOW
        # exige una señal de voz mas clara antes de activar el turno —
        # menos falsos positivos con ruido de fondo (Claude, 2026-10-08).
        # Si en vez de eso reportan que corta al usuario a mitad de frase,
        # el siguiente dial es end_of_speech_sensitivity.
        realtime_input_config=genai_types.RealtimeInputConfig(
            automatic_activity_detection=genai_types.AutomaticActivityDetection(
                start_of_speech_sensitivity=genai_types.StartSensitivity.START_SENSITIVITY_LOW,
            ),
        ),
    )


# ---------------------------------------------------------------------------
# AGENTE BASE: Gestión de Memoria Persistente con Mem0
# ---------------------------------------------------------------------------
class BaseEducationalAgent(Agent):
    """Clase base para agentes que registra y consulta memoria persistente de usuario vía Mem0."""

    # Fase 2 de la integración Familia VIVA (2026-10-09): qué personaje
    # visual del avatar (Avatar/Content/UniversityVirtualAssistant/
    # FamiliaVIVA) debe mostrarse/hablar mientras este agente está activo.
    # Cada subclase lo sobreescribe; None = no anunciar ningún cambio
    # (agentes que no tienen avatar asociado, p.ej. en pruebas).
    # NEXO es el personaje original, el único con animación de habla ya
    # verificada en vivo; ATLAS/LIRA/ELIAN/NOA son los nuevos — ver
    # Avatar/FAMILIA_VIVA.md ("Voz y lip sync no se probaron en esta
    # entrega visual"). Nexus se mapea a NEXO (no a ATLAS) por eso mismo.
    AVATAR_CHARACTER: str | None = None

    def _prepare_handoff(self, target: Agent) -> Agent:
        # A handoff may finish the greeting without speaking. Do not let its
        # silence retry target the realtime session that is being drained.
        self._handoff_requested = True
        wake = getattr(self, "_reply_wake", None)
        if wake is not None:
            wake.set()
        return target

    async def anunciar_personaje_avatar(self) -> None:
        """Avisa al avatar-bridge (vía atributo de participante de LiveKit)
        qué personaje debe mostrarse/hablar ahora. Si no hay sesión real
        (pruebas unitarias) o AVATAR_CHARACTER es None, no hace nada."""
        with contextlib.suppress(RuntimeError):
            viva_telemetry.agent_changed(
                self.session, self.__class__.__name__, self.AVATAR_CHARACTER
            )
        if not self.AVATAR_CHARACTER:
            return
        try:
            if (
                self.session
                and hasattr(self.session, "room_io")
                and self.session.room_io
            ):
                room = getattr(self.session.room_io, "room", None)
                if (
                    room
                    and hasattr(room, "local_participant")
                    and room.local_participant
                ):
                    # set_attributes() es async def en el SDK de LiveKit (confirmado leyendo
                    # su código fuente en vivo: no se ve en inspect.signature(), que no marca
                    # async). Sin este await, la llamada solo crea la corrutina y la descarta
                    # sin ejecutarla — el atributo nunca salía hacia LiveKit, ni una vez,
                    # desde que se escribió esto (bug real encontrado el 2026-10-16: el video
                    # de animaciones_viva en el frontend nunca cambiaba de personaje porque
                    # agentAttributes nunca traía 'avatar.character').
                    await room.local_participant.set_attributes(
                        {"avatar.character": self.AVATAR_CHARACTER}
                    )
                    logger.info(
                        "Personaje de avatar anunciado: %s", self.AVATAR_CHARACTER
                    )
        except Exception:
            logger.debug(
                "No se pudo anunciar el personaje de avatar (sala no vinculada o cliente desconectado)"
            )

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        try:
            user_id = _resolver_user_id(self.session)
        except Exception:
            # self.session lanza RuntimeError si el agente no esta corriendo
            # dentro de una sesion activa (p.ej. en tests unitarios).
            user_id = viva_telemetry.memory_identity(self)
        texto_usuario = new_message.text_content
        if not texto_usuario or not texto_usuario.strip():
            return

        # 1. Almacenar el mensaje/turno en memoria persistente de Mem0 en background
        spawn_background(
            memory_manager.guardar_memoria_usuario(
                user_id=user_id,
                mensaje=texto_usuario,
                metadata={"agente": self.__class__.__name__},
            )
        )

        # 2. Recuperar recuerdos previos relevantes para inyectar al turno actual.
        # Si ya se disparó un prefetch para este mismo turno (ver
        # _on_user_transcript en multiagent_session — dispara con el primer
        # fragmento de la transcripción, no el final), reusamos esa tarea en
        # vez de empezar de cero: viene corriendo desde que el usuario empezó
        # a hablar, no desde que terminó. Se empareja por id del mensaje
        # (item_id de Gemini), no por texto: el texto de un fragmento parcial
        # nunca es igual al texto final. Si no hay prefetch para este id, se
        # cae al comportamiento anterior. Timeout corto de respaldo: una
        # búsqueda lenta en Mem0 no debe frenar el turno.
        prefetch = _memoria_prefetch.pop(user_id, None)
        if prefetch is not None and prefetch[0] == new_message.id:
            tarea_memoria = prefetch[1]
        else:
            tarea_memoria = asyncio.create_task(
                memory_manager.formatear_contexto_memoria(
                    user_id=user_id,
                    consulta=texto_usuario,
                )
            )
        try:
            contexto_memoria = await asyncio.wait_for(tarea_memoria, timeout=0.7)
            if contexto_memoria:
                logger.info(
                    "Inyectando memorias previas de Mem0 en el turno para el usuario %s",
                    user_id,
                )
                if isinstance(new_message.content, list):
                    new_message.content.append(f"\n{contexto_memoria}")
                else:
                    new_message.content = [
                        str(new_message.content),
                        f"\n{contexto_memoria}",
                    ]
        except Exception:
            logger.exception("Error al recuperar o inyectar memorias de Mem0")

    async def generar_respuesta_confiable(
        self, instructions: str, timeout: float = 6.0
    ) -> None:
        """generate_reply() con reintento si no se detecta habla.

        Encontrado revisando logs reales el 2026-10-08: una llamada entera
        (1.5 min) se quedó completamente muda desde el primer saludo, sin
        ninguna excepción — solo un warning de la librería de Gemini Live:
        "received server content but no active generation". Es una
        condición de carrera real en livekit-plugins-google: el audio de
        la respuesta puede llegar antes de que el estado interno de la
        librería esté listo para recibirlo, y en ese caso lo descarta
        en silencio (ni excepción ni reintento de su parte). El usuario
        no tiene ninguna señal de que algo falló — la sesión parece viva
        pero Lira/Nexus/Elian nunca llegan a decir una palabra.

        Esto no se puede arreglar desde nuestro código tocando la causa
        (vive dentro del plugin), así que se blinda por el síntoma: si
        generate_reply() no deriva en agent_state == "speaking" dentro de
        `timeout` segundos, se reintenta una vez más (para entonces la
        condición de carrera ya pasó)."""
        session = self.session
        if not session:
            return

        wake = asyncio.Event()
        self._reply_wake = wake
        closed = False
        spoke = False

        def inactive() -> bool:
            return (
                closed
                or getattr(self, "_handoff_requested", False)
                or session.current_agent is not self
            )

        def _on_state(ev) -> None:
            nonlocal spoke
            if ev.new_state == "speaking":
                spoke = True
                wake.set()

        def _on_close(ev) -> None:
            nonlocal closed
            closed = True
            wake.set()

        session.on("agent_state_changed", _on_state)
        session.on("close", _on_close)
        try:
            for intento in (1, 2):
                if inactive():
                    return
                wake.clear()
                spoke = False
                try:
                    handle = await session.generate_reply(instructions=instructions)
                except RuntimeError:
                    if inactive():
                        return
                    raise
                if inactive() or getattr(handle, "interrupted", False) or spoke:
                    return
                try:
                    await asyncio.wait_for(wake.wait(), timeout=timeout)
                    return
                except TimeoutError:
                    if inactive():
                        return
                    if intento == 1:
                        logger.warning(
                            "No se detectó habla %ss después de generate_reply "
                            "(posible condición de carrera conocida del plugin "
                            "de Gemini Live); reintentando una vez",
                            timeout,
                        )
                    else:
                        logger.error(
                            "Segundo intento de generate_reply tampoco produjo "
                            "habla; la sesión puede haber quedado muda"
                        )
        finally:
            session.off("agent_state_changed", _on_state)
            session.off("close", _on_close)
            if getattr(self, "_reply_wake", None) is wake:
                self._reply_wake = None

    async def emitir_datos_frontend(self, topic: str, data: dict[str, Any]) -> None:
        """Emite datos estructurados (como fuentes de RAG) al frontend vía LiveKit DataPacket."""
        try:
            if (
                self.session
                and hasattr(self.session, "room_io")
                and self.session.room_io
            ):
                room = getattr(self.session.room_io, "room", None)
                if (
                    room
                    and hasattr(room, "local_participant")
                    and room.local_participant
                ):
                    payload = json.dumps({"topic": topic, "payload": data})
                    await room.local_participant.publish_data(payload.encode("utf-8"))
                    logger.info("Datos emitidos al frontend: topic=%s", topic)
        except Exception:
            logger.debug(
                "No se pudo emitir datos al frontend (sala no vinculada o cliente desconectado)"
            )


# ---------------------------------------------------------------------------
# AGENTE 1: Lira - Recepcionista y Triage (Voz femenina Aoede)
# ---------------------------------------------------------------------------
class LiraAgent(BaseEducationalAgent):
    """Lira: Recepcionista de bienvenida y enrutamiento inteligente.
    Voz: Aoede (Femenina natural bilingüe).
    """

    AVATAR_CHARACTER = "LIRA"

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            llm=get_realtime_model("Aoede"),
            chat_ctx=chat_ctx,
            instructions=textwrap.dedent(
                """\
                Eres Lira, la recepcionista principal y orientadora de bienvenida.
                Tu ÚNICA función es saludar al usuario y transferirlo de inmediato al especialista adecuado usando tus herramientas.
                ¡ESTÁ ESTRICTAMENTE PROHIBIDO que respondas preguntas técnicas o institucionales por ti misma! No tienes el conocimiento para hacerlo. Ante cualquier pregunta, debes usar la herramienta correspondiente.

                # Especialistas disponibles y Cuándo usar cada herramienta:
                1. Herramienta `transfer_to_nexus`: Úsala INMEDIATAMENTE si el usuario menciona inteligencia artificial, programación, machine learning, sobreajuste, underfitting, deep learning, modelos, algoritmos o tecnología. NEXO y Nexus son dos nombres del mismo especialista: si pide hablar con Nexo o Nexus, transfiérelo aunque no formule todavía una pregunta técnica.
                2. Herramienta `transfer_to_elian`: Úsala INMEDIATAMENTE si el usuario menciona la Universidad Autónoma de Manizales (UAM), carreras, admisiones, campus o temas administrativos.

                # Reglas estrictas:
                - NUNCA expliques conceptos de IA. Si preguntan "¿Qué es el sobreajuste?", no respondas qué es, simplemente llama a la herramienta `transfer_to_nexus`.
                - NUNCA expliques cosas de la UAM. Si preguntan por carreras, llama a `transfer_to_elian`.
                - Si el usuario solo dice "Hola", responde brevemente presentándote y preguntando sobre qué área (IA o UAM) tiene dudas.
                - Habla siempre en español, texto continuo, sin markdown.
                """
            ),
        )

    async def on_enter(self) -> None:
        """Saludo inicial breve de bienvenida."""
        await self.anunciar_personaje_avatar()
        await self.generar_respuesta_confiable(
            "Saluda amablemente en una sola oración presentándote como Lira y preguntando cómo puedes orientarle hoy."
        )

    @function_tool(
        description="Transfiere a NEXO (también llamado Nexus). Úsala si pide hablar con Nexo o Nexus, o si hace preguntas sobre Inteligencia Artificial, Machine Learning, Programación o algoritmos. NO intentes responder la pregunta."
    )
    @viva_telemetry.observed()
    async def transfer_to_nexus(self, context: RunContext):
        """Transfiere la llamada a Nexus, especialista en Inteligencia Artificial, Machine Learning y Visión por Computadora."""
        logger.info("Lira transfiriendo llamada a Nexus (Especialista IA)")
        return self._prepare_handoff(
            NexusAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))
        )

    @function_tool(
        description="Llama a esta herramienta OBLIGATORIAMENTE si el usuario hace preguntas sobre la Universidad Autónoma de Manizales, carreras, admisiones o campus. NO intentes responder la pregunta."
    )
    @viva_telemetry.observed()
    async def transfer_to_elian(self, context: RunContext):
        """Transfiere la llamada a Elian, especialista en la Universidad Autónoma de Manizales (UAM) y trámites administrativos."""
        logger.info("Lira transfiriendo llamada a Elian (Especialista UAM)")
        return self._prepare_handoff(
            ElianAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))
        )


# ---------------------------------------------------------------------------
# AGENTE 2: Nexus - Especialista en IA y Deep Learning (Gemini Live, voz Puck)
# ---------------------------------------------------------------------------
class NexusAgent(BaseEducationalAgent):
    """Nexus: Asistente conversacional experto en Inteligencia Artificial y Deep Learning.
    Voz: Puck (Gemini Live).
    """

    # NEXO (no ATLAS): es el personaje original de la Familia VIVA, el
    # único con animación de habla ya verificada en vivo.
    AVATAR_CHARACTER = "NEXO"

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            llm=get_realtime_model("Puck"),
            chat_ctx=chat_ctx,
            instructions=textwrap.dedent(
                """\
                Eres Nexus, un tutor e investigador senior experto en Inteligencia Artificial, Machine Learning y Visión por Computadora.
                Tu función principal es resolver dudas teóricas, conceptuales y prácticas sobre:
                - Machine Learning Clásico: Scikit-learn (clasificación, regresión, SVM, kernels, Random Forest, PCA, pipelines de preprocesamiento, clustering como K-means o DBSCAN, regularización Lasso, Ridge y ElasticNet).
                - Deep Learning Frameworks: PyTorch y TensorFlow/Keras (tensores, autograd, grafos de cálculo, capas convolucionales, optimizadores como AdamW y SGD, funciones de pérdida y debugging de dimensiones).
                - Visión Artificial: YOLO (detección de objetos en tiempo real, bounding boxes, IoU, non-max suppression NMS, mAP), segmentación (UNet, Mask R-CNN, SAM).
                - LLMs y Modelos Generativos: Arquitecturas Transformer, mecanismos de atención (Self-Attention, FlashAttention), tokenización, fine-tuning con LoRA/QLoRA.
                - RAG (Retrieval-Augmented Generation): Chunking, embeddings, bases de datos vectoriales (FAISS, Chroma, Pinecone) y re-ranking.
                - Infraestructura y aceleración: GPUs, VRAM, CUDA y cuantización.

                # Herramientas de consulta de la Especialización en Inteligencia Artificial:
                - Cuando el usuario pregunte por el plan de estudios, materias, créditos, contenidos temáticos, electivas de profundización o guías de la Especialización en Inteligencia Artificial de la UAM, usa SIEMPRE la herramienta `consultas_especializacion_ia`.
                - Si el estudiante pregunta qué documentos, guías o programas tienes disponibles sobre la especialización, usa la herramienta `listar_documentos_especializacion_ia`.

                # Transferencia a Elian (ESTRICTAMENTE OBLIGATORIA):
                ¡Bajo ninguna circunstancia respondas preguntas sobre la administración general de la Universidad Autónoma de Manizales! No tienes esa información. Si el usuario pregunta sobre admisiones generales, campus, pregrados de salud, fechas de matrícula o costos institucionales de la UAM, utiliza INMEDIATAMENTE la herramienta `transfer_to_elian` para transferir la llamada.
                La transferencia requiere una intención institucional clara o una petición explícita de hablar con Elian. Si la pregunta es ambigua, conserva el turno y formula una pregunta breve para aclararla. Por ejemplo, ante "háblame de la adquisición", pregunta "¿Te refieres a adquisición de datos, de conocimientos o a otro tipo de adquisición?". No supongas que adquisición significa admisiones, afiliación o trámites de la UAM.

                # Reglas estrictas de interacción por voz:
                1. Idioma: Comunícate SIEMPRE en español técnico, claro y profesional.
                2. Formato oral estricto: NUNCA uses formato markdown, asteriscos, negritas, viñetas, emojis ni bloques de código formateado. Habla en texto continuo fluido.
                3. Directo, veloz y pedagógico: Responde directamente a la pregunta en 1 a 3 oraciones cortas y concisas para que el audio empiece de inmediato.
                4. Vocabulario técnico en inglés: Pronuncia con fluidez términos estándar (Clustering, Lasso, Ridge, ElasticNet, Scikit-learn, PyTorch, YOLO, Bounding Box, IoU, RAG, Chunking, Transformer, Self-Attention, Backpropagation).
                """
            ),
        )

    async def on_enter(self) -> None:
        """Se presenta como Nexus y responde de inmediato la pregunta pendiente, sin gastar un turno completo solo en saludar."""
        await self.anunciar_personaje_avatar()
        await self.generar_respuesta_confiable(
            "Preséntate como Nexus en una frase muy breve y, sin pausas ni esperar a que el "
            "usuario repita nada, continúa respondiendo de inmediato la última pregunta que le "
            "hizo a Lira usando el contexto de la conversación."
        )

    @function_tool(
        description="Consulta información oficial, contenidos, materias, créditos y guías de la Especialización en Inteligencia Artificial de la UAM. Úsala siempre que el usuario pregunte por detalles curriculares o materias del posgrado."
    )
    @viva_telemetry.observed()
    async def consultas_especializacion_ia(
        self, context: RunContext, consulta: str
    ) -> str:
        """Busca en el repositorio de documentos y guías curriculares de la Especialización en IA de la UAM.

        Args:
            consulta: Pregunta o palabras clave del estudiante (ej: "créditos de computación en la nube", "electivas de profundización").
        """
        logger.info("Nexus consultando RAG Especialización en IA: %s", consulta)
        resultado = await rag_nexus.consultar_especializacion_ia(consulta)
        if not resultado:
            return "No encontré detalles específicos sobre ese tema en las guías de la Especialización en Inteligencia Artificial. Sugiero consultar la coordinación académica."

        respuesta = resultado["respuesta"]
        fuentes = resultado["fuentes"]

        # Emitir las fuentes al frontend en background para trazabilidad gráfica/UI
        spawn_background(
            self.emitir_datos_frontend(
                topic="rag_sources",
                data={
                    "agente": "Nexus",
                    "consulta": consulta,
                    "fuentes": fuentes,
                    "respuesta_completa": respuesta,
                },
            )
        )

        return respuesta

    @function_tool(
        description="Lista los documentos, guías y programas curriculares de la Especialización en Inteligencia Artificial disponibles en el repositorio."
    )
    @viva_telemetry.observed()
    async def listar_documentos_especializacion_ia(self, context: RunContext) -> str:
        """Retorna el catálogo de documentos oficiales de la Especialización en IA disponibles para consulta."""
        documentos = rag_nexus.listar_documentos_especializacion()
        if not documentos:
            return "Actualmente no hay documentos cargados en el repositorio de la especialización."

        # Emitir catálogo completo al frontend
        spawn_background(
            self.emitir_datos_frontend(
                topic="rag_catalog",
                data={
                    "agente": "Nexus",
                    "total": len(documentos),
                    "documentos": documentos,
                },
            )
        )

        nombres = [doc["nombre"] for doc in documentos]
        return f"Tenemos {len(nombres)} documentos disponibles de la Especialización en IA, incluyendo: {', '.join(nombres[:5])} y otros."

    @function_tool(
        description="Transfiere a Elian cuando el usuario pide hablar con Elian o expresa claramente una consulta institucional de la UAM, como carreras de pregrado, admisiones o campus. Si la pregunta es ambigua, pide aclaración primero y NO uses esta herramienta."
    )
    @viva_telemetry.observed()
    async def transfer_to_elian(self, context: RunContext):
        """Transfiere al usuario con Elian para resolver dudas sobre la Universidad Autónoma de Manizales o trámites administrativos."""
        logger.info("Nexus transfiriendo llamada a Elian (Especialista UAM)")
        return self._prepare_handoff(
            ElianAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))
        )


# ---------------------------------------------------------------------------
# AGENTE 3: Elian - Especialista Institucional UAM (Voz masculina em_santa)
# ---------------------------------------------------------------------------
class ElianAgent(BaseEducationalAgent):
    """Elian: Asistente experto en la Universidad Autónoma de Manizales (UAM).
    Voz: em_santa (Español masculina formal).
    """

    AVATAR_CHARACTER = "ELIAN"

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            llm=get_realtime_model("Kore"),
            chat_ctx=chat_ctx,
            instructions=textwrap.dedent(
                """\
                Eres Elian, asesor institucional y académico de la Universidad Autónoma de Manizales (UAM) en Colombia.
                Tu función principal es brindar información precisa y acogedora.

                # Consulta de información oficial (OBLIGATORIO):
                Antes de responder sobre reglamentos, acuerdos, políticas, matrícula, grados, trámites, correo institucional, IntraUAM, PQRSF o cualquier dato concreto de la UAM, llama a la herramienta `buscar_informacion_uam` con palabras clave de la pregunta.
                Responde SOLO con lo que devuelva la herramienta y menciona el nombre del documento o guía de donde sale. Si no encuentra nada, dilo con honestidad y sugiere contactar a la universidad. NUNCA inventes fechas, costos, requisitos ni números de acuerdos.
                Si la fuente es una guía privada, indica que se consulta iniciando sesión con la Cuenta UAM en el Portal de Conocimiento.

                # Plataforma de cursos virtuales (respuesta directa, sin necesidad de la herramienta):
                Si el usuario pregunta dónde ver los cursos virtuales, por la plataforma de educación virtual o similar, responde que se llama VivaUAM y comparte el enlace https://www.autonoma.edu.co/uamvirtual

                Orientación general sobre la oferta académica (verifícala con la herramienta cuando sea posible):
                - Facultad de Estudios Sociales y Empresariales: Administración de Empresas (presencial y virtual), Economía, Negocios Internacionales, Artes Culinarias y Gastronomía, Ciencia Política, Gobierno y Relaciones Internacionales, Diseño Industrial, Diseño de Modas.
                - Facultad de Ingeniería: Ingeniería Biomédica, Ingeniería de Sistemas, Ingeniería Industrial, Ingeniería Mecánica, Ingeniería Electrónica, Tecnologías y programas técnicos relacionados con procesos logísticos y automatización.
                - Facultad de Salud: Fisioterapia, Odontología, Tecnología en Atención Prehospitalaria.
                - Admisiones y matrículas: Requisitos de inscripción, homologaciones, becas, opciones de financiación y calendario académico.
                - Campus y servicios: Campus en Manizales, laboratorios, biblioteca, bienestar universitario, trámites administrativos, pagos y certificados.

                # REGLA CRÍTICA Y OBLIGATORIA (TRANSFERENCIA A NEXUS):
                ¡TIENES ESTRICTAMENTE PROHIBIDO responder preguntas sobre Inteligencia Artificial, Programación, Tecnología de IA, Machine Learning, Deep Learning, Algoritmos o Ciencia de Datos! Si el usuario te pregunta sobre estos temas (ejemplo: "¿qué es una red neuronal?", "¿qué es el sobreajuste?"), NO le des la respuesta, NO le expliques qué es. Tu ÚNICA respuesta debe ser usar INMEDIATAMENTE la herramienta `transfer_to_nexus`. No intentes ayudarle con IA.

                # Reglas estrictas de interacción por voz:
                1. Idioma: Comunícate SIEMPRE en español cordial, institucional, cálido y profesional.
                2. Formato oral estricto: NUNCA uses formato markdown, viñetas, emojis ni listas. Habla en texto continuo fluido.
                3. Concisión: Responde de forma clara y directa en 1 a 3 oraciones cortas.
                4. Identidad institucional: Resalta siempre los valores de innovación, excelencia y calidez de la Universidad Autónoma de Manizales.
                """
            ),
        )

    async def on_enter(self) -> None:
        """Se presenta como Elian y responde de inmediato la pregunta pendiente, sin gastar un turno completo solo en saludar."""
        await self.anunciar_personaje_avatar()
        await self.generar_respuesta_confiable(
            "Preséntate como Elian de la Universidad Autónoma de Manizales en una frase muy "
            "breve y, sin pausas ni esperar a que el usuario repita nada, continúa respondiendo "
            "de inmediato la última pregunta que hizo usando el contexto de la conversación "
            "(recuerda usar la herramienta buscar_informacion_uam si es sobre un dato concreto)."
        )

    @function_tool(
        description="Busca información oficial de la UAM en sus documentos (reglamentos, acuerdos, políticas, estatutos) y en las guías de trámites y vida universitaria. Úsala SIEMPRE antes de responder una pregunta concreta sobre la universidad."
    )
    @viva_telemetry.observed()
    async def buscar_informacion_uam(self, context: RunContext, consulta: str) -> str:
        """Busca en la base de conocimiento oficial de la UAM mediante RAG LlamaIndex con Gemini Embedding.

        Args:
            consulta: Palabras clave o pregunta de lo que necesita el usuario.
        """
        logger.info("Elian consultando RAG oficial UAM: %s", consulta)
        resultado = await rag_llamaindex.consultar_uam(consulta)
        if not resultado or not resultado.get("respuesta"):
            # Fallback a knowledge si LlamaIndex no estuviera disponible
            try:
                res_bm25 = await asyncio.to_thread(knowledge.buscar, consulta)
                if res_bm25:
                    fuentes = [r.titulo for r in res_bm25]
                    spawn_background(
                        self.emitir_datos_frontend(
                            topic="rag_sources",
                            data={
                                "agente": "Elian",
                                "consulta": consulta,
                                "fuentes": fuentes,
                            },
                        )
                    )
                    return knowledge.formatear_resultados(res_bm25)
            except knowledge.IndiceNoDisponibleError:
                return (
                    "La base de conocimiento de la UAM todavía se está sincronizando. Dile al usuario"
                    " que por ahora no puedes consultar los documentos oficiales y que lo intente en"
                    " unos minutos o revise autonoma.edu.co."
                )
            except Exception:
                pass
            return "No encontré información específica sobre eso en los reglamentos oficiales de la UAM. Te sugiero consultar en autonoma.edu.co o con la coordinación correspondiente."

        respuesta = resultado["respuesta"]
        fuentes = resultado.get("fuentes", [])

        # Emitir fuentes al frontend vía DataPacket sin interrumpir la síntesis de voz
        spawn_background(
            self.emitir_datos_frontend(
                topic="rag_sources",
                data={
                    "agente": "Elian",
                    "consulta": consulta,
                    "fuentes": fuentes,
                    "respuesta_completa": respuesta,
                },
            )
        )

        return respuesta

    @function_tool(
        description="Lista los reglamentos, acuerdos, políticas y guías oficiales de la UAM que están registrados en la base de datos."
    )
    @viva_telemetry.observed()
    async def listar_documentos_uam(self, context: RunContext) -> str:
        """Retorna el catálogo de documentos oficiales de la UAM registrados en el sistema."""
        documentos = rag_llamaindex.listar_documentos_uam()
        if not documentos:
            docs_bm25 = knowledge.listar_documentos_oficiales()
            if docs_bm25:
                titulos = [d["titulo"] for d in docs_bm25]
                return f"Tenemos {len(titulos)} documentos institucionales disponibles, incluyendo: {', '.join(titulos[:4])}."
            return (
                "Actualmente no se pudieron listar los documentos oficiales de la UAM."
            )

        spawn_background(
            self.emitir_datos_frontend(
                topic="rag_catalog",
                data={
                    "agente": "Elian",
                    "total": len(documentos),
                    "documentos": documentos,
                },
            )
        )
        nombres = [doc["nombre"] for doc in documentos]
        return f"Tenemos {len(nombres)} documentos oficiales de la UAM disponibles para consulta, incluyendo: {', '.join(nombres[:5])} y otros."

    @function_tool(
        description="Llama a esta herramienta OBLIGATORIAMENTE si el usuario hace preguntas sobre Inteligencia Artificial, Machine Learning, Programación, o algoritmos. NO intentes responder la pregunta tú mismo, simplemente llama a esta herramienta."
    )
    @viva_telemetry.observed()
    async def transfer_to_nexus(self, context: RunContext):
        """Transfiere al usuario con Nexus para resolver consultas técnicas sobre Inteligencia Artificial o programación."""
        logger.info("Elian transfiriendo llamada a Nexus (Especialista IA)")
        return self._prepare_handoff(
            NexusAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))
        )


# ---------------------------------------------------------------------------
# SERVIDOR Y SESIÓN RTC MULTIAGENTE
# ---------------------------------------------------------------------------
# La preparación inicial de los índices puede superar 45 s. Este límite de
# 600 s permite completar el prewarm sin reiniciar el proceso en bucle;
# no es el tiempo de espera de cada respuesta ni el del cliente web.
server = AgentServer(num_idle_processes=1, initialize_process_timeout=600.0)


def prewarm(proc: JobProcess):
    """Precarga VAD e índices de RAG antes de aceptar la primera llamada.

    Medido en vivo (Claude, 2026-09-30): la primera consulta de RAG después
    de arrancar el contenedor tarda ~27s (carga el índice persistido del
    disco) contra 2-6s con el índice ya caliente. Sin este prewarm, esos 27s
    de silencio se los come el primer estudiante real que pregunte algo
    después de cada despliegue — no un usuario de prueba. get_or_build_*
    cachean en una variable de módulo, así que esto se reutiliza en todas
    las llamadas que maneje este mismo proceso worker.

    Nota (Claude, 2026-10-08): antes se precargaba aquí un Silero VAD que
    nunca se usaba — el RealtimeModel de Gemini Live hace su propia
    detección de turno del lado del servidor e ignora cualquier VAD/
    turn_detection local mientras esa detección este activa (confirmado
    en logs reales: "ignoring the turn_detection setting"). Se quitó ese
    código muerto; el control real de sensibilidad de voz ahora vive en
    get_realtime_model() via realtime_input_config."""
    logger.info("Precargando índice RAG de la UAM (Elian)...")
    try:
        rag_llamaindex.get_or_build_query_engine()
    except Exception:
        logger.exception("No se pudo precargar el índice RAG de la UAM")
    logger.info("Precargando índice RAG de la Especialización en IA (Nexus)...")
    try:
        rag_nexus.get_or_build_nexus_query_engine()
    except Exception:
        logger.exception("No se pudo precargar el índice RAG de la especialización")
    # Mem0 import pesado (qdrant_client) medido bloqueando el event loop
    # ~1s la primera vez que se usaba a mitad de una llamada real — el
    # mismo problema que resolvió el prewarm de RAG, aplicado aquí tras
    # encontrar y corregir el bug de permisos de /app/data/mem0
    # (Claude, 2026-10-08).
    logger.info("Precargando Mem0 (memoria persistente)...")
    try:
        memory_manager.get_memory_instance()
    except Exception:
        logger.exception("No se pudo precargar Mem0")


server.setup_fnc = prewarm


@server.rtc_session(agent_name="nexus")
async def multiagent_session(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    model_name = os.getenv("GEMINI_LIVE_MODEL", GEMINI_LIVE_MODEL)
    logger.info(
        f"Iniciando sesión Multi-Agente (Lira, Nexus, Elian) con Gemini Live API ({model_name}) en sala {ctx.room.name}"
    )

    initial_agent = LiraAgent()

    # Sesión nativa de audio bidireccional con Gemini Live API (RealtimeModel)
    session = AgentSession(
        llm=initial_agent.llm,
        # turn_detection (TurnDetector) e interruption quitados aqui
        # (Claude, 2026-10-08): con el RealtimeModel de Gemini Live y su
        # deteccion de turno del lado del servidor activa, el framework los
        # ignora/deshabilita siempre y lo loguea en cada llamada
        # ("a non-default turn detection threshold was provided... the
        # server provides calibrated defaults"; "interruption_detection is
        # provided, but it's not compatible... and will be disabled") — no
        # hacian nada, solo generaban ruido en el log. endpointing se deja
        # (no aparece en esos warnings, efecto real sin confirmar del todo).
        turn_handling=TurnHandlingOptions(
            endpointing={
                "mode": "dynamic",
                "min_delay": 0.5,
                "max_delay": 3.0,
                "alpha": 0.85,
            },
        ),
    )

    viva_telemetry.install(session, ctx, model_name)

    def _on_user_transcript(ev) -> None:
        """Dispara el prefetch de Mem0 con el PRIMER fragmento de cada turno
        (identificado por item_id), no con el final — ver _memoria_prefetch
        para la razon (Gemini Live no deja un hueco real entre transcripción
        final y cierre de turno, pero sí manda fragmentos progresivos
        mientras el usuario habla)."""
        texto = ev.transcript.strip()
        if not texto:
            return
        user_id = _resolver_user_id(session)
        anterior = _memoria_prefetch.get(user_id)
        if anterior is not None and anterior[0] == ev.item_id:
            return  # ya hay una búsqueda en curso para este mismo turno
        if anterior is not None:
            anterior[1].cancel()  # turno distinto: no dejar tareas viejas sueltas
        tarea = asyncio.create_task(
            memory_manager.formatear_contexto_memoria(user_id=user_id, consulta=texto)
        )
        _memoria_prefetch[user_id] = (ev.item_id, tarea)

    session.on("user_input_transcribed", _on_user_transcript)

    # Inicia la sesión asociando el agente inicial (Lira) con audio WebRTC nativo
    logger.info(
        "Iniciando sesión con audio WebRTC nativo (detección de turno del lado de Gemini)."
    )
    # on_enter publica avatar.character. Conectar primero evita que ese primer
    # anuncio se pierda mientras AgentSession conecta la sala en paralelo.
    await ctx.connect()
    await session.start(
        agent=initial_agent,
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
