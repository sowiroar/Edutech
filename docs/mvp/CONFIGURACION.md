# Configuración de servicios y entorno local

Revisado el 17 de octubre de 2026 contra el código de `backp-fase1`.
`.env.example` documenta el despliegue general; es una plantilla, no un archivo
de secretos ni prueba de que todos esos servicios participen en cada modalidad.
Los ejemplos de LiveKit `devkey` / `secret` son valores públicos de desarrollo.
La clave Google y la contraseña del portal están vacías en la plantilla rastreada.

| Variables | Uso actual | Perfil local de voz |
|---|---|---|
| `GOOGLE_API_KEY`, `GEMINI_LIVE_MODEL` | Gemini Live, voz bidireccional | Obligatorios en `.env.voice` |
| `GOOGLE_API_KEY` | También RAG, embeddings y Mem0 | Misma clave; servicios y modelos adicionales pueden tener cuotas diferentes |
| `LIVEKIT_URL`, `LIVEKIT_URL_INTERNAL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | Transporte RTC y emisión de tokens | Compose fija servidor local y credenciales dev; no importar las de UAM |
| `AGENT_NAME` | Despacho desde frontend | `nexus`, igual al registro del worker actual |
| `PORTAL_CONOCIMIENTO_URL`, `PORTAL_CONOCIMIENTO_USER`, `PORTAL_CONOCIMIENTO_APP_PASSWORD` | Lectura del portal por knowledge-sync | Opcionales, en `.env.voice`; sin usuario/contraseña solo recorrido público |
| `SYNC_INTERVAL_HOURS` | Frecuencia de knowledge-sync | 24 por defecto |
| `OLLAMA_*`, `WHISPER_*` | Servicios del Compose histórico | No se inician en este perfil Gemini Live |
| `AVATAR_*` | Medios, bridge y renderer | Renderer no iniciado; voz del agente audible |

RAG usa `models/gemini-embedding-2`; Mem0 además usa `gemini-2.5-flash`, según
el código actual. Una prueba correcta del modelo Live no certifica estos modelos,
la indexación, recuperación o persistencia. No cambiarlos por copiar una plantilla.

## Configuración privada

1. Desde Edutech: `python3 scripts/voice_demo.py init`.
2. Completar `.env.voice` con la configuración autorizada. Si existe un archivo
   recibido de Jacobo, copiar únicamente las variables de Google y, si aplica,
   las del portal; conservar LiveKit y volúmenes locales definidos por Compose.
3. Ejecutar `python3 scripts/voice_demo.py doctor` y
   `python3 scripts/voice_demo.py config`. No muestran valores. El doctor verifica
   presencia, no validez de la clave. No publicar la salida de `docker inspect`
   ni de `docker compose config` sin `--quiet`: pueden contener secretos.
4. `python3 scripts/voice_demo.py up`; abrir http://localhost:3500.

`.env.voice` y sus respaldos `.env.voice.*` están excluidos de Git. En esta Mac,
el archivo fuente `.env-jacobo` permanece fuera de los repositorios y con permisos
600; `.env.voice` también tiene 600. Las plantillas deben conservar valores vacíos
para claves reales. Nunca copiar secretos a AGENTS/CLAUDE, PR, capturas o informes.

## Validación de configuración en esta Mac

La configuración recibida de Jacobo se aplicó sin copiar endpoints RTC de UAM.
`doctor` y Compose quiet correctos. Una llamada directa acotada a
`gemini-3.8-live` recibió 84002 bytes de audio y `turn_complete=true`, ante una
frase sintética de prueba. No se guardó audio, clave ni token en la evidencia.
Prueba basada en la [guía oficial de Gemini Live](https://ai.google.dev/gemini-api/docs/live-api/capabilities).
No equivale a aceptación de micrófono/navegador, handoffs, avatar o servidor UAM.

La preparación inicial de RAG puede enviar documentos institucionales al proveedor
Google y consume su API, según la implementación existente de Jacobo. Los índices
se guardan en volúmenes locales y `down` los conserva. Consultar VALIDACION.md
para separar resultados reales de servicios simplemente arrancados.
