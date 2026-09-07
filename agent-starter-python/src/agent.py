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


class NexusAgent(Agent):
    """Nexus: Asistente conversacional experto en Inteligencia Artificial y Deep Learning."""

    def __init__(self, model_name: str = "nexus") -> None:
        super().__init__(
            # Inferencia de lenguaje local mediante Ollama con 100% GPU y 90s timeout
            llm=openai.LLM(
                model=model_name,
                base_url=OLLAMA_BASE_URL,
                api_key="ollama",
                client=ollama_client,
                timeout=httpx.Timeout(connect=30.0, read=90.0, write=30.0, pool=30.0),
                temperature=0.6,
            ),
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
                3. Concisión conversacional: Responde en 1 a 3 oraciones por turno. Sé directo al núcleo de la duda técnica. Si el concepto requiere mayor profundidad, invita al estudiante a profundizar en el siguiente turno para evitar monólogos.
                4. Vocabulario técnico en inglés: Pronuncia con fluidez los términos técnicos en inglés estándar (Scikit-learn, PyTorch, TensorFlow, YOLO, Bounding Box, IoU, RAG, Chunking, Transformer, Self-Attention, Backpropagation, Gradient Descent, Loss, GPU, CUDA).
                5. Soluciones de código habladas: Describe la solución con lenguaje hablado claro (por ejemplo: 'en Scikit-learn puedes instanciar un Pipeline con StandardScaler y SVC antes de ajustar los datos').
                """
            ),
        )

    async def on_enter(self):
        """Saludo proactivo de bienvenida al ingresar el estudiante a la sesión."""
        await self.session.generate_reply(
            instructions=(
                "Saluda con entusiasmo y calidez en español en una sola frase breve. "
                "Preséntate como Nexus, especialista en Inteligencia Artificial y Deep Learning, "
                "y pregunta en qué duda técnica o proyecto de IA puedes colaborar hoy."
            ),
            allow_interruptions=True,
        )


def get_tts_engine():
    """Retorna exclusivamente el motor local Kokoro TTS (OpenAI-compatible) con voz masculina en español (em_alex).
    100% local, sin uso de TTS en la nube.
    """
    logger.info(f"Usando exclusivamente Kokoro TTS local en {KOKORO_BASE_URL} (voz masculina 'em_alex').")
    return openai.TTS(
        model="kokoro",
        voice="em_alex",
        api_key="not-needed",
        base_url=KOKORO_BASE_URL,
        response_format="wav",
    )


server = AgentServer()


def prewarm(proc: JobProcess):
    """Precarga Silero VAD en memoria al iniciar el proceso del servidor."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="nexus")
async def nexus_session(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Pipeline de voz en streaming con soporte nativo para español latino (es-419)
    session = AgentSession(
        # Silero VAD precargado localmente
        vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
        # Speech-to-text: Deepgram Nova-3 en español latino (es-419) con refuerzo de keyterms técnicos
        stt=inference.STT(
            model="deepgram/nova-3",
            language="es-419",
            extra_kwargs={
                "keyterm": [
                    "Scikit-learn",
                    "YOLO",
                    "TensorFlow",
                    "PyTorch",
                    "RAG",
                    "Transformer",
                    "Backpropagation",
                    "Gradient Descent",
                    "Bounding Box",
                    "IoU",
                    "NMS",
                    "Segmentación",
                    "SAM",
                    "CUDA",
                    "VRAM",
                    "Kernel",
                    "LoRA",
                    "Overfitting",
                ],
            },
        ),
        # Text-to-speech (TTS): Kokoro local si está activo en 8880, o LiveKit Cloud TTS
        tts=get_tts_engine(),
        turn_handling=TurnHandlingOptions(
            # LiveKit TurnDetector: modelo acústico y semántico multilingüe que evita cortes prematuros
            turn_detection=inference.TurnDetector(),
            # Interrupción adaptativa (barge-in): distingue pausas y confirmaciones ("ajá", "sí") de interrupciones reales
            interruption={"mode": "adaptive"},
            # Generación preventiva: predice y genera tokens antes de que finalice el turno del usuario
            preemptive_generation={"enabled": True},
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
