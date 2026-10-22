# Agentes de Edutech

Backend Python con LiveKit Agents y Gemini Live para conversación educativa.
Conserva los roles y transferencias de LIRA, Nexus y ELIAN, junto con RAG,
memoria y emisión de eventos de telemetría. `src/agent.py` es el punto de entrada.

## Arranque recomendado

Utilizar el [perfil local completo](../README.md) desde la raíz del repositorio:
`python scripts/voice_demo.py up`. Este perfil prepara el almacenamiento y RAG
antes del worker, y conecta LiveKit, frontend y telemetría. No necesita Unreal,
Ollama, Whisper ni una GPU NVIDIA para el recorrido Gemini Live.

## Desarrollo aislado

Usar Python compatible con `pyproject.toml` y **uv**; CI utiliza Python 3.12.
Desde esta carpeta:

```sh
uv sync --locked
uv run python src/agent.py dev
```

Antes de ejecutar el agente, configurar el entorno autorizado: conexión y claves
de LiveKit, `GOOGLE_API_KEY`, `GEMINI_LIVE_MODEL` y servicios de memoria/RAG.
Consultar [configuración](../docs/mvp/CONFIGURACION.md). La raíz `.env.voice` se
inyecta mediante Compose; ejecutar Python directamente no reproduce por sí solo
esa infraestructura. No copiar credenciales de otro entorno a ejemplos o commits.

## Personajes y presentación

| Clase | Personaje anunciado | Voz |
|---|---|---|
| LiraAgent | LIRA | Aoede |
| NexusAgent | NEXO | Puck |
| ElianAgent | ELIAN | Kore |

El worker se registra como `nexus` y la sesión comienza con LIRA. La sala se
conecta antes de `session.start()` para que el primer `avatar.character` llegue
al frontend. Las transferencias actualizan ese atributo; las voces no se eligen
en el visor. Los tres personajes tienen modelos web verificados localmente;
la aceptación artística sigue siendo independiente.

Las consultas documentales de NEXO y ELIAN conservan síntesis con Gemini 2.5 Flash.
`src/rag_config.py` fija temperatura 0,2 y un presupuesto de razonamiento interno
de 512 tokens para reducir la espera; no recorta la respuesta ni sustituye las
fuentes por conocimiento general. Este ajuste no se aplica al modelo de voz.
La inicialización en frío de NEXO se ejecuta fuera del bucle de audio.

## Pruebas

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
```

`tests/test_avatar_startup.py` verifica el anuncio inicial sin inicializar modelos
cloud ni RAG. Las pruebas de código no reemplazan la aceptación de voz humana,
la evaluación de recuperación documental ni la validación institucional.
No ejecutar simulaciones con costos de proveedor por una limpieza documental.

[Correspondencia agente/voz/avatar](../docs/mvp/AVATAR_AGENT_MAPPING.md),
[telemetría](../docs/mvp/TELEMETRY_IMPLEMENTACION.md) y
[flujo de contribución](../docs/mvp/FLUJO.md).
