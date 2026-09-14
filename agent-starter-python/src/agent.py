from __future__ import annotations

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
    room_io,
)
from livekit.plugins import ai_coustics, openai, silero

logger = logging.getLogger("agent-multi")

load_dotenv(".env.local")

# Configuración dinámica de endpoints locales / Docker
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
KOKORO_BASE_URL = os.getenv("KOKORO_BASE_URL", "http://localhost:8880/v1")
WHISPER_BASE_URL = os.getenv("WHISPER_BASE_URL", "http://whisper-stt:8000/v1")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nexus")

# Cliente HTTP con timeout de 60s para evitar cortes en inferencia local con GPU
ollama_client = py_openai.AsyncClient(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    http_client=httpx.AsyncClient(
        timeout=httpx.Timeout(connect=15.0, read=60.0, write=15.0, pool=15.0),
        follow_redirects=True,
    ),
)


def get_llm_engine(model_name: str | None = None) -> openai.LLM:
    """Instancia del motor LLM compatible con OpenAI apuntando a Ollama local o nube."""
    actual_model = model_name or OLLAMA_MODEL
    return openai.LLM(
        model=actual_model,
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        client=ollama_client,
        temperature=0.6,
    )


def get_tts_engine(voice: str = "ef_dora") -> openai.TTS:
    """Retorna el motor local Kokoro TTS (OpenAI-compatible) con la voz en español seleccionada:
    - ef_dora: Voz femenina cálida en español (Lira - Recepción y Triage).
    - em_alex: Voz masculina técnica en español (Nexus - Especialista en IA).
    - em_santa: Voz masculina formal en español (Elian - Especialista UAM).
    Usa model='tts-1' para activar el streaming binario de audio de LiveKit.
    """
    return openai.TTS(
        model="tts-1",
        voice=voice,
        api_key="not-needed",
        base_url=KOKORO_BASE_URL,
        response_format="wav",
    )


# ---------------------------------------------------------------------------
# AGENTE 1: Lira - Recepcionista y Triage (Voz femenina ef_dora)
# ---------------------------------------------------------------------------
class LiraAgent(Agent):
    """Lira: Recepcionista de bienvenida y enrutamiento inteligente.
    Voz: ef_dora (Español femenina).
    """

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            llm=get_llm_engine(),
            tts=get_tts_engine("ef_dora"),
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
class NexusAgent(Agent):
    """Nexus: Asistente conversacional experto en Inteligencia Artificial y Deep Learning.
    Voz: em_alex (Español masculina).
    """

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            llm=get_llm_engine(),
            tts=get_tts_engine("em_alex"),
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

                # Transferencia a Elian (ESTRICTAMENTE OBLIGATORIA):
                ¡Bajo ninguna circunstancia respondas preguntas sobre la Universidad Autónoma de Manizales! No tienes esa información. Si el usuario pregunta sobre admisiones, programas, campus, fechas de matrícula o costos de la UAM, utiliza INMEDIATAMENTE la herramienta `transfer_to_elian` para transferir la llamada.

                # Reglas estrictas de interacción por voz:
                1. Idioma: Comunícate SIEMPRE en español técnico, claro y profesional.
                2. Formato oral estricto: NUNCA uses formato markdown, asteriscos, negritas, viñetas, emojis ni bloques de código formateado. Habla en texto continuo fluido.
                3. Directo, veloz y pedagógico: Responde directamente a la pregunta en 1 a 3 oraciones cortas y concisas para que el audio empiece de inmediato.
                4. Vocabulario técnico en inglés: Pronuncia con fluidez términos estándar (Clustering, Lasso, Ridge, ElasticNet, Scikit-learn, PyTorch, YOLO, Bounding Box, IoU, RAG, Chunking, Transformer, Self-Attention, Backpropagation).
                """
            ),
        )

    async def on_enter(self) -> None:
        """Saluda brevemente confirmando que está listo para abordar el tema de Inteligencia Artificial."""
        await self.session.generate_reply(
            instructions="Saluda brevemente en una sola oración como Nexus, indicando que tomas la palabra para responder la consulta de inteligencia artificial."
        )

    @function_tool(
        description="Llama a esta herramienta OBLIGATORIAMENTE si el usuario hace preguntas sobre la Universidad Autónoma de Manizales, carreras, admisiones o campus. NO intentes responder la pregunta tú mismo."
    )
    async def transfer_to_elian(self, context: RunContext):
        """Transfiere al usuario con Elian para resolver dudas sobre la Universidad Autónoma de Manizales o trámites administrativos."""
        logger.info("Nexus transfiriendo llamada a Elian (Especialista UAM)")
        return ElianAgent(chat_ctx=self.chat_ctx.copy(exclude_instructions=True))


# ---------------------------------------------------------------------------
# AGENTE 3: Elian - Especialista Institucional UAM (Voz masculina em_santa)
# ---------------------------------------------------------------------------
class ElianAgent(Agent):
    """Elian: Asistente experto en la Universidad Autónoma de Manizales (UAM).
    Voz: em_santa (Español masculina formal).
    """

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            llm=get_llm_engine(),
            tts=get_tts_engine("em_santa"),
            chat_ctx=chat_ctx,
            instructions=textwrap.dedent(
                """\
                Eres Elian, asesor institucional y académico de la Universidad Autónoma de Manizales (UAM) en Colombia.
                Tu función principal es brindar información precisa y acogedora. Utiliza la siguiente base de conocimiento:
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
        """Saluda brevemente confirmando que atenderá los temas de la Universidad Autónoma de Manizales."""
        await self.session.generate_reply(
            instructions="Saluda brevemente en una sola oración como Elian de la Universidad Autónoma de Manizales, dispuesto a colaborar con la información institucional."
        )

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
    """Precarga Silero VAD en memoria con tiempos calibrados para rapidez de respuesta sin cortar al usuario."""
    logger.info("Precargando Silero VAD local...")
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=0.50,  # 500ms de silencio antes de marcar fin de segmento
        min_speech_duration=0.08,  # 80ms de voz para filtrar chasquidos o ruidos
        prefix_padding_duration=0.5,  # 500ms de padding previo para no perder la primera palabra
    )


server.setup_fnc = prewarm


@server.rtc_session(agent_name="nexus")
async def multiagent_session(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    whisper_url = os.getenv("WHISPER_BASE_URL", WHISPER_BASE_URL)
    whisper_mod = os.getenv("WHISPER_MODEL", WHISPER_MODEL)

    logger.info(
        f"Iniciando sesión Multi-Agente (Lira, Nexus, Elian) en sala {ctx.room.name} con STT Whisper ({whisper_mod}) en {whisper_url}"
    )

    # Pipeline de voz en streaming 100% local (Silero VAD + Faster-Whisper STT + Ollama LLM + Kokoro TTS)
    # LiraAgent es el agente inicial activo (voz femenina ef_dora)
    session = AgentSession(
        llm=get_llm_engine(),
        vad=ctx.proc.userdata.get("vad")
        or silero.VAD.load(
            min_silence_duration=0.50,
            min_speech_duration=0.08,
            prefix_padding_duration=0.5,
        ),
        stt=openai.STT(
            base_url=whisper_url,
            model=whisper_mod,
            api_key="not-needed",
            language="es",
        ),
        tts=get_tts_engine("ef_dora"),
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
            preemptive_generation={
                "enabled": True,
                "preemptive_tts": True,
                "max_speech_duration": 10.0,
                "max_retries": 3,
            },
        ),
    )

    # Inicia la sesión asociando el agente Lira y la cancelación de ruido
    await session.start(
        agent=LiraAgent(),
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
