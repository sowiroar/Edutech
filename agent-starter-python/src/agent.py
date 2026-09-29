from __future__ import annotations

import asyncio
import json
import logging
import os
import textwrap

import httpx
import openai as py_openai
from dotenv import load_dotenv
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
    inference,
    llm,
    room_io,
)
from livekit.plugins import ai_coustics, google, silero

import knowledge
import memory_manager
import rag_llamaindex
import rag_nexus

logger = logging.getLogger("agent-multi")

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Configuración de Google Gemini Live API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")

# Prefetch de memoria Mem0: la transcripción final llega antes de que el turno
# se dé por cerrado (el endpointing dinámico espera entre 0.5 y 3s de silencio
# para confirmar que el usuario terminó). Arrancamos la búsqueda en Mem0 ahí,
# en paralelo con esa espera, para que on_user_turn_completed casi nunca tenga
# que esperar sus 0.7s de tope. Una entrada por user_id (la más reciente pisa
# a la anterior); se consume y se descarta en on_user_turn_completed
# (Claude, 2026-09-29).
_memoria_prefetch: dict[str, tuple[str, asyncio.Task]] = {}


def _resolver_user_id(session) -> str:
    user_id = "estudiante_uam"
    try:
        if session and hasattr(session, "room_io") and session.room_io:
            participant = getattr(session.room_io, "participant", None)
            if participant and getattr(participant, "identity", None):
                user_id = participant.identity
    except Exception:
        pass
    return user_id


def get_realtime_model(voice: str = "Aoede") -> google.realtime.RealtimeModel:
    """Instancia del motor Gemini Live API (RealtimeModel).
    Voces soportadas:
    - Aoede: Femenina natural y relajada en español/inglés (Lira - Recepción y Triage).
    - Puck: Masculina dinámica, alegre y técnica (Nexus - Especialista en IA).
    - Charon: Masculina formal, calmada y profesional (Elian - Especialista UAM).
    """
    api_key = os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY or "mock-key-for-tests"
    model = os.getenv("GEMINI_LIVE_MODEL") or GEMINI_LIVE_MODEL or "gemini-3.8-live"
    return google.realtime.RealtimeModel(
        model=model,
        voice=voice,
        api_key=api_key,
        temperature=0.7,
    )


# ---------------------------------------------------------------------------
# AGENTE BASE: Gestión de Memoria Persistente con Mem0
# ---------------------------------------------------------------------------
class BaseEducationalAgent(Agent):
    """Clase base para agentes que registra y consulta memoria persistente de usuario vía Mem0."""

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        try:
            user_id = _resolver_user_id(self.session)
        except Exception:
            # self.session lanza RuntimeError si el agente no esta corriendo
            # dentro de una sesion activa (p.ej. en tests unitarios).
            user_id = "estudiante_uam"
        texto_usuario = new_message.text_content
        if not texto_usuario or not texto_usuario.strip():
            return

        # 1. Almacenar el mensaje/turno en memoria persistente de Mem0 en background
        asyncio.create_task(
            memory_manager.guardar_memoria_usuario(
                user_id=user_id,
                mensaje=texto_usuario,
                metadata={"agente": self.__class__.__name__},
            )
        )

        # 2. Recuperar recuerdos previos relevantes para inyectar al turno actual.
        # Si ya se disparó un prefetch para este mismo texto (ver
        # _on_user_transcript en multiagent_session), reusamos esa tarea en vez
        # de empezar de cero: normalmente ya terminó o le falta poco, porque
        # viene corriendo desde que el STT dio la transcripción final, en
        # paralelo con la espera de endpointing. Si no hay prefetch o no
        # coincide el texto, se cae al comportamiento anterior. Timeout corto
        # de respaldo: una búsqueda lenta en Mem0 no debe frenar el turno.
        texto_normalizado = texto_usuario.strip()
        prefetch = _memoria_prefetch.pop(user_id, None)
        if prefetch is not None and prefetch[0] == texto_normalizado:
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
                    new_message.content = [str(new_message.content), f"\n{contexto_memoria}"]
        except Exception:
            logger.exception("Error al recuperar o inyectar memorias de Mem0")

    async def emitir_datos_frontend(self, topic: str, data: dict[str, Any]) -> None:
        """Emite datos estructurados (como fuentes de RAG) al frontend vía LiveKit DataPacket."""
        try:
            if self.session and hasattr(self.session, "room_io") and self.session.room_io:
                room = getattr(self.session.room_io, "room", None)
                if room and hasattr(room, "local_participant") and room.local_participant:
                    payload = json.dumps({"topic": topic, "payload": data})
                    await room.local_participant.publish_data(payload.encode("utf-8"))
                    logger.info("Datos emitidos al frontend: topic=%s", topic)
        except Exception:
            logger.debug("No se pudo emitir datos al frontend (sala no vinculada o cliente desconectado)")


# ---------------------------------------------------------------------------
# AGENTE 1: Lira - Recepcionista y Triage (Voz femenina Aoede)
# ---------------------------------------------------------------------------
class LiraAgent(BaseEducationalAgent):
    """Lira: Recepcionista de bienvenida y enrutamiento inteligente.
    Voz: Aoede (Femenina natural bilingüe).
    """

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
                1. Herramienta `transfer_to_nexus`: Úsala INMEDIATAMENTE si el usuario menciona inteligencia artificial, programación, machine learning, sobreajuste, underfitting, deep learning, modelos, algoritmos o tecnología.
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
        await self.session.generate_reply(
            instructions="Saluda amablemente en una sola oración presentándote como Lira y preguntando cómo puedes orientarle hoy."
        )

    @function_tool(
        description="Llama a esta herramienta OBLIGATORIAMENTE si el usuario hace preguntas sobre Inteligencia Artificial, Machine Learning, Programación, o algoritmos. NO intentes responder la pregunta."
    )
    async def transfer_to_nexus(self, context: RunContext):
        """Transfiere la llamada a Nexus, especialista en Inteligencia Artificial, Machine Learning y Visión por Computadora."""
        logger.info("Lira transfiriendo llamada a Nexus (Especialista IA)")
        return NexusAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))

    @function_tool(
        description="Llama a esta herramienta OBLIGATORIAMENTE si el usuario hace preguntas sobre la Universidad Autónoma de Manizales, carreras, admisiones o campus. NO intentes responder la pregunta."
    )
    async def transfer_to_elian(self, context: RunContext):
        """Transfiere la llamada a Elian, especialista en la Universidad Autónoma de Manizales (UAM) y trámites administrativos."""
        logger.info("Lira transfiriendo llamada a Elian (Especialista UAM)")
        return ElianAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))


# ---------------------------------------------------------------------------
# AGENTE 2: Nexus - Especialista en IA y Deep Learning (Voz masculina em_alex)
# ---------------------------------------------------------------------------
class NexusAgent(BaseEducationalAgent):
    """Nexus: Asistente conversacional experto en Inteligencia Artificial y Deep Learning.
    Voz: em_alex (Español masculina).
    """

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
        if self.session:
            await self.session.generate_reply(
                instructions=(
                    "Preséntate como Nexus en una frase muy breve y, sin pausas ni esperar a que el "
                    "usuario repita nada, continúa respondiendo de inmediato la última pregunta que le "
                    "hizo a Lira usando el contexto de la conversación."
                )
            )

    @function_tool(
        description="Consulta información oficial, contenidos, materias, créditos y guías de la Especialización en Inteligencia Artificial de la UAM. Úsala siempre que el usuario pregunte por detalles curriculares o materias del posgrado."
    )
    async def consultas_especializacion_ia(self, context: RunContext, consulta: str) -> str:
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
        asyncio.create_task(
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
    async def listar_documentos_especializacion_ia(self, context: RunContext) -> str:
        """Retorna el catálogo de documentos oficiales de la Especialización en IA disponibles para consulta."""
        documentos = rag_nexus.listar_documentos_especializacion()
        if not documentos:
            return "Actualmente no hay documentos cargados en el repositorio de la especialización."

        # Emitir catálogo completo al frontend
        asyncio.create_task(
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
        description="Llama a esta herramienta OBLIGATORIAMENTE si el usuario hace preguntas sobre la Universidad Autónoma de Manizales general, carreras de pregrado, admisiones o campus. NO intentes responder la pregunta tú mismo."
    )
    async def transfer_to_elian(self, context: RunContext):
        """Transfiere al usuario con Elian para resolver dudas sobre la Universidad Autónoma de Manizales o trámites administrativos."""
        logger.info("Nexus transfiriendo llamada a Elian (Especialista UAM)")
        return ElianAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))


# ---------------------------------------------------------------------------
# AGENTE 3: Elian - Especialista Institucional UAM (Voz masculina em_santa)
# ---------------------------------------------------------------------------
class ElianAgent(BaseEducationalAgent):
    """Elian: Asistente experto en la Universidad Autónoma de Manizales (UAM).
    Voz: em_santa (Español masculina formal).
    """

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            llm=get_realtime_model("Charon"),
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
        if self.session:
            await self.session.generate_reply(
                instructions=(
                    "Preséntate como Elian de la Universidad Autónoma de Manizales en una frase muy "
                    "breve y, sin pausas ni esperar a que el usuario repita nada, continúa respondiendo "
                    "de inmediato la última pregunta que hizo usando el contexto de la conversación "
                    "(recuerda usar la herramienta buscar_informacion_uam si es sobre un dato concreto)."
                )
            )

    @function_tool(
        description="Busca información oficial de la UAM en sus documentos (reglamentos, acuerdos, políticas, estatutos) y en las guías de trámites y vida universitaria. Úsala SIEMPRE antes de responder una pregunta concreta sobre la universidad."
    )
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
                    asyncio.create_task(
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
        asyncio.create_task(
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
    async def listar_documentos_uam(self, context: RunContext) -> str:
        """Retorna el catálogo de documentos oficiales de la UAM registrados en el sistema."""
        documentos = rag_llamaindex.listar_documentos_uam()
        if not documentos:
            docs_bm25 = knowledge.listar_documentos_oficiales()
            if docs_bm25:
                titulos = [d["titulo"] for d in docs_bm25]
                return f"Tenemos {len(titulos)} documentos institucionales disponibles, incluyendo: {', '.join(titulos[:4])}."
            return "Actualmente no se pudieron listar los documentos oficiales de la UAM."

        asyncio.create_task(
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
    async def transfer_to_nexus(self, context: RunContext):
        """Transfiere al usuario con Nexus para resolver consultas técnicas sobre Inteligencia Artificial o programación."""
        logger.info("Elian transfiriendo llamada a Nexus (Especialista IA)")
        return NexusAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))


# ---------------------------------------------------------------------------
# SERVIDOR Y SESIÓN RTC MULTIAGENTE
# ---------------------------------------------------------------------------
server = AgentServer(num_idle_processes=1)


def prewarm(proc: JobProcess):
    """Precarga Silero VAD para detección local si es requerida."""
    logger.info("Precargando Silero VAD local...")
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=0.50,
        min_speech_duration=0.08,
        prefix_padding_duration=0.5,
    )


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
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(
                version="v1-mini",
                unlikely_threshold=0.55,
            ),
            endpointing={
                "mode": "dynamic",
                "min_delay": 0.5,
                "max_delay": 3.0,
                "alpha": 0.85,
            },
            interruption={
                "enabled": True,
                "mode": "adaptive",
                "min_duration": 0.45,
                "false_interruption_timeout": 2.0,
                "resume_false_interruption": True,
            },
        ),
    )

    def _on_user_transcript(ev) -> None:
        """Dispara el prefetch de Mem0 en cuanto el STT da la transcripción
        final, sin esperar a que el turno se cierre (ver _memoria_prefetch)."""
        if not ev.is_final:
            return
        texto = ev.transcript.strip()
        if not texto:
            return
        user_id = _resolver_user_id(session)
        tarea = asyncio.create_task(
            memory_manager.formatear_contexto_memoria(user_id=user_id, consulta=texto)
        )
        _memoria_prefetch[user_id] = (texto, tarea)

    session.on("user_input_transcribed", _on_user_transcript)

    # Inicia la sesión asociando el agente inicial (Lira) y la mejora de audio
    await session.start(
        agent=initial_agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )

    # Conecta al participante a la sala WebRTC
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
