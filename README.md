# Edutech · Familia VIVA

Plataforma de conversación educativa con LiveKit, Gemini Live y frontend Next.js.
La presentación puede ser **Voz** o **Avatar**. LIRA de Juan recibe la conversación
con Aoede; al transferir a Nexus se muestra NEXO con Puck y a Elian, ELIAN con Kore.
Cada modelo procede de su escena original de Unreal.

Los avatares se dibujan en el navegador. **Unreal no tiene que permanecer abierto**:
se utiliza para preparar y exportar los modelos una sola vez.

[Auditoría y plan de aceptación del 22 de octubre](docs/validation/2026-10-22-avatar-audit/README.md):
arranque RAG, caché de modelos y generación de candidatos desde Mac.

## Arranque local

Requisitos: Python 3 y Docker con Compose activo. Desde esta carpeta:

```powershell
python scripts/voice_demo.py init
```

Completar `GOOGLE_API_KEY` y `GEMINI_LIVE_MODEL` en `.env.voice`, con acceso a los
modelos que usa el proyecto. El archivo es privado y no se versiona. Después:

```powershell
python scripts/voice_demo.py doctor
python scripts/voice_demo.py up
python scripts/voice_demo.py ps
```

En macOS/Linux, usar `python3` si corresponde. La primera preparación de RAG
puede tardar varios minutos; `rag-init` debe terminar correctamente antes del agente.
El servicio necesita conexión a Google. No requiere ejecutar Ollama, Whisper ni CUDA.

- Aplicación: http://localhost:3000 o http://localhost:3500; ambos sirven la misma web.
- Panel privado: http://localhost:3500/admin; contraseña en `TELEMETRY_ADMIN_PASSWORD`.
- Vista sin llamada: `/avatar-preview?character=LIRA`, `?character=NEXO` o `?character=ELIAN`.
- Reconstruir solo la web: `python scripts/voice_demo.py web`.
- Detener conservando los datos: `python scripts/voice_demo.py down`.

Si el puerto 3000 está ocupado por el frontend histórico, revisar ese proceso
antes de iniciar otro. No borrar volúmenes para resolver un conflicto de puertos.

## Instalar los avatares en otro equipo

Git incluye el visor, los exportadores y los manifiestos de las versiones revisadas.
**Los GLB y fondos se entregan por separado dentro del equipo**: contienen recursos
de terceros que no deben publicarse como una biblioteca de assets descargables.
Consultar [instalación de modelos](agent-starter-react/public/avatars/README.md) y
[procedencia y condiciones](THIRD_PARTY_AVATARS.md). Sin los archivos, la voz sigue
funcionando y la web no anuncia modelos disponibles.

Una vez instalados, elegir **Avatar** e iniciar la llamada. El modelo sigue el
atributo `avatar.character` del agente; el nombre del worker `nexus` no determina
qué personaje está hablando. Se carga un modelo a la vez.

## Estado verificado

| Área | Estado |
|---|---|
| LIRA de Juan, NEXO y ELIAN | Exportación, reposo y reproducción de voz verificados localmente |
| Cambio LIRA → NEXO → ELIAN | Verificado por atributo del agente y modelo visible |
| Presentación de voz | Disponible aunque falte o falle el modelo |
| Telemetría | Colector y panel existentes; métricas con cobertura explícita |
| Apariencia | NEXO con rostro nativo LOD3 y rig original; los tres comparten el fondo UAM. Aprobación artística pendiente |
| ATLAS, NOVA y NOA | Assets Unreal disponibles; agentes de voz aún no implementados |
| Boca | RMS y bandas de audio para apertura/redondeo/extensión; no sincronización fonética |
| UAM, Moodle y concurrencia | No certificados por estas pruebas locales |

Medición del 21 de octubre: a 960 × 540, ambos avatares mantuvieron 30 FPS.
RAM privada residente media del navegador: **597 MiB LIRA / 556 MiB NEXO**;
servicios Docker: **1,67 / 1,69 GiB**. Se usó la GPU integrada AMD 740M.
Son muestras de una llamada por vez, no presupuestos máximos ni requisitos universales.
[Informe completo de RAM, GPU y CPU](docs/validation/2026-10-21-avatar-resources/README.md).
La [prueba posterior de labios y tres agentes](docs/validation/2026-10-21-avatar-speech-style/README.md)
verifica los cambios visuales y la llamada; no sustituye el benchmark de RAM/GPU.
El [ajuste de espera y piel de NEXO](docs/validation/2026-10-21-nexo-latency/README.md)
documenta la reducción de tiempo en consultas, su alcance y el acabado mate del visor.
La [recuperación del arranque de LIRA](docs/validation/2026-10-21-lira-startup/README.md)
comprueba que una desconexión permite reintentar y que LIRA vuelve a cargar con audio.

## Organización

| Ruta | Contenido |
|---|---|
| `agent-starter-react/` | Interfaz, WebGL, tokens de sesión y panel |
| `agent-starter-python/` | Agentes, transferencias, RAG y memoria |
| `telemetry-service/`, `contracts/` | Colector, persistencia y contratos |
| `knowledge-sync/` | Sincronización del conocimiento |
| `scripts/` | Arranque, exportación y comprobaciones |
| `data/` | Documentos; resultados locales y bases generadas se excluyen de Git |
| `Avatar/` | Submódulo que fija una versión del proyecto Unreal |
| `avatar-bridge/`, `avatar-render/` | Recorrido nativo histórico, separado del visor web |
| `docs/mvp/`, `docs/validation/` | Guías vigentes y evidencia fechada |

El repositorio hermano `../Avatar/` se usa para autoría de Unreal. No copiar su
Content ni sus builds a este repositorio y no actualizar el submódulo con trabajo
sin publicar. El perfil local es `compose.voice.yml`; el Compose histórico no es
el comando de arranque de esta entrega.

## Desarrollo y entrega

La base de desarrollo es **main**; `backp-fase1` es una referencia de compatibilidad.
Trabajar en una rama `feature/`, `bugfix/` o `chore/` y entregar por PR a `main`.
Usar `EDUTECH_SKIP_DEPLOY=1` al operar Git para evitar los hooks históricos de despliegue.

- [Índice técnico y estado](docs/mvp/README.md).
- [Frontend: desarrollo y pruebas](agent-starter-react/README.md).
- [Agente: desarrollo y pruebas](agent-starter-python/README.md).
- [Avatar web y exportación](docs/mvp/AVATAR_WEB.md).
- [Flujo del equipo](docs/mvp/FLUJO.md) y [operación](docs/mvp/RUNBOOK.md).
- [Entrega preparada del 21 de octubre](docs/mvp/ENTREGA_WEB_2026-10-21.md).

No incluir `.env`, claves, tokens, cachés, exportaciones brutas ni bases de datos
locales en commits o adjuntos públicos. Publicar código no equivale a desplegar UAM.
