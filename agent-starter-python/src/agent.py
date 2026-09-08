import logging
import textwrap

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)
import os
from urllib.parse import urlparse
import httpx
import openai as py_openai
from livekit.plugins import ai_coustics, openai, silero

logger = logging.getLogger("agent-nexus")

load_dotenv(".env.local")

# Configuración dinámica de endpoints locales / Docker
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
KOKORO_BASE_URL = os.getenv("KOKORO_BASE_URL", "http://localhost:8880/v1")

# Cliente HTTP con timeout de 60s para evitar cortes en inferencia local con GPU
ollama_client = py_openai.AsyncClient(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    http_client=httpx.AsyncClient(
        timeout=httpx.Timeout(connect=15.0, read=60.0, write=15.0, pool=15.0),
        follow_redirects=True,
    ),
)

WHISPER_BASE_URL = os.getenv("WHISPER_BASE_URL", "http://whisper-stt:8000/v1")
whisper_client = py_openai.AsyncClient(
    base_url=WHISPER_BASE_URL,
    api_key="not-needed",
    http_client=httpx.AsyncClient(
        timeout=httpx.Timeout(connect=15.0, read=30.0, write=15.0, pool=15.0),
        follow_redirects=True,
    ),
)


def get_llm_engine(model_name: str = "nexus") -> openai.LLM:
    """Instancia del motor LLM compatible con OpenAI apuntando a Ollama local."""
    return openai.LLM(
        model=model_name,
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        client=ollama_client,
        temperature=0.6,
    )


class NexusAgent(Agent):
    """Nexus: Asistente conversacional experto en Inteligencia Artificial y Deep Learning."""

    def __init__(self, model_name: str = "nexus") -> None:
        super().__init__(
            llm=get_llm_engine(model_name),
            instructions=textwrap.dedent(
                """\
                Eres Nexus, un tutor e investigador senior experto en Inteligencia Artificial, Machine Learning y Visión por Computadora.
                Tu función principal es resolver dudas teóricas, conceptuales y prácticas sobre:
                - Machine Learning Clásico: Scikit-learn (clasificación, regresión, SVM, kernels, Random Forest, PCA, pipelines de preprocesamiento, métricas como F1, ROC-AUC y matriz de confusión).
                - Deep Learning Frameworks: PyTorch y TensorFlow/Keras (tensores, autograd, grafos de cálculo, capas convolucionales, optimizadores como AdamW y SGD, funciones de pérdida y debugging de dimensiones).
                - Visión Artificial: YOLO (detección de objetos en tiempo real, bounding boxes, IoU, non-max suppression NMS, mAP), Detección de objetos y Segmentación (semántica con UNet, por instancias con Mask R-CNN y modelos fundacionales como SAM).
                - LLMs y Modelos Generativos: Arquitecturas Transformer, mecanismos de atención (Self-Attention, FlashAttention), tokenización, pre-entrenamiento y fine-tuning con LoRA/QLoRA.
                - RAG (Retrieval-Augmented Generation): Chunking de texto, modelos de embeddings, bases de datos vectoriales (FAISS, Chroma, Pinecone) y re-ranking de contexto.
                - Sistemas de Agentes y Multiagente: Agentes autónomos, llamado de funciones (tool-calling), memoria contextual, planificación, patrones ReAct y handoffs.
                - Infraestructura y aceleración: GPUs, VRAM, precisión mixta (FP16/BF16), CUDA y cuantización.

                # Reglas estrictas de interacción por voz:
                1. Idioma: Comunícate SIEMPRE en español con entonación natural, pedagógica, clara y profesional.
                2. Formato oral estricto: Estás hablando en voz alta por un sintetizador de audio. NUNCA uses formato markdown, asteriscos (*), negritas (**), almohadillas (#), viñetas (-), emojis ni bloques de código formateado. Habla en texto continuo fluido.
                3. Directo, veloz y pedagógico: Responde SIEMPRE de manera directa a la pregunta o duda técnica del estudiante en 1 a 3 oraciones cortas y concisas. Usa oraciones breves para que la síntesis de audio empiece de inmediato. NUNCA respondas con evasivas ni preguntas retóricas. Da la explicación conceptual o práctica inmediatamente.
                4. Vocabulario técnico en inglés: Pronuncia con fluidez los términos técnicos en inglés estándar (Clustering, Lasso, Ridge, ElasticNet, Scikit-learn, PyTorch, TensorFlow, YOLO, Bounding Box, IoU, RAG, Chunking, Transformer, Self-Attention, Backpropagation, Gradient Descent, Loss, GPU, CUDA).
                5. Soluciones de código habladas: Describe la solución con lenguaje hablado claro (por ejemplo: 'en Scikit-learn puedes instanciar un Pipeline con StandardScaler y SVC antes de ajustar los datos').
                """
            ),
        )



def get_tts_engine():
    """Retorna exclusivamente el motor local Kokoro TTS (OpenAI-compatible) con voz masculina en español (em_alex).
    100% local, sin uso de TTS en la nube.
    Usa model='tts-1' para seleccionar el transporte de bytes directos de LiveKit.
    """
    return openai.TTS(
        model="tts-1",
        voice="em_alex",
        api_key="not-needed",
        base_url=KOKORO_BASE_URL,
        response_format="wav",
    )


server = AgentServer(num_idle_processes=1)


def prewarm(proc: JobProcess):
    """Precarga Silero VAD en memoria con tiempos calibrados para rapidez de respuesta sin cortar al usuario."""
    logger.info("Precargando Silero VAD local...")
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=0.50,    # 500ms de silencio antes de marcar fin de segmento
        min_speech_duration=0.08,    # 80ms de voz para filtrar chasquidos o ruidos
        prefix_padding_duration=0.5, # 500ms de padding previo para no perder la primera palabra
    )


server.setup_fnc = prewarm


@server.rtc_session(agent_name="nexus")
async def nexus_session(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    whisper_base_url = os.getenv("WHISPER_BASE_URL", "http://whisper-stt:8000/v1")
    whisper_model = os.getenv("WHISPER_MODEL", "base")

    logger.info(f"Iniciando sesión Nexus en sala {ctx.room.name} con STT Whisper en {whisper_base_url}")

    # Pipeline de voz en streaming 100% local (Silero VAD + Faster-Whisper STT + Ollama LLM + Kokoro TTS)
    session = AgentSession(
        # LLM local Ollama explícito para evitar fallback a LiveKit Cloud Inference
        llm=get_llm_engine(),
        # Silero VAD precargado localmente
        vad=ctx.proc.userdata.get("vad") or silero.VAD.load(
            min_silence_duration=0.50,
            min_speech_duration=0.08,
            prefix_padding_duration=0.5,
        ),
        # Speech-to-text: Faster-Whisper local vía microservicio OpenAI
        stt=openai.STT(
            client=whisper_client,
            model=whisper_model,
            language="es",
        ),
        # Text-to-speech (TTS): Kokoro local (em_alex)
        tts=get_tts_engine(),
        turn_handling=TurnHandlingOptions(
            # TurnDetector v1-mini: modelo acústico local en CPU para evitar cortes prematuros sin depender de la nube
            turn_detection=inference.TurnDetector(
                version="v1-mini",
                unlikely_threshold=0.55,  # Umbral calibrado: espera si detecta entonación de pensamiento o pausa intermedia
            ),
            # Endpointing dinámico: adapta los tiempos de espera a las pausas naturales del usuario
            endpointing={
                "mode": "dynamic",
                "min_delay": 0.5,   # Límite inferior para cierres ágiles cuando el TurnDetector está seguro
                "max_delay": 3.0,   # Límite superior para pausas de duda
                "alpha": 0.85,
            },
            # Interrupción: distingue interrupciones reales de ruidos o carraspeos y reanuda si fue falsa interrupción
            interruption={
                "enabled": True,
                "mode": "adaptive",
                "min_duration": 0.45,
                "false_interruption_timeout": 2.0,
                "resume_false_interruption": True,
            },
            preemptive_generation={"enabled": False},
        ),
    )

    # Inicia la sesión asociando el agente Nexus y el filtro de cancelación de ruido acústico
    await session.start(
        agent=NexusAgent(),
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

