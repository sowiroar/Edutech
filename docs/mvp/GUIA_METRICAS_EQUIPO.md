# VIVA: qué podemos probar y cómo leer la telemetría

**Corte: 17 de octubre de 2026, hora Colombia.** Para Jacobo, Santiago y el equipo.

## Estado real

La voz y la telemetría están integradas en **`backp-fase1`**, mediante los PR #8 y #9. La base revisada es `43d42d9`, con CI aprobado.

Podemos probar conversación por voz, panel privado, mensajes con ocultación básica,
herramientas, RAG, cambios de agente, consumo y errores. Hay evidencia local de
Gemini, cambio Lira → Nexus y consulta RAG. **Falta revisión en UAM**.

La integración audiovisual de los seis avatares y su rendimiento concurrente siguen
pendientes de validación. No declaramos terminado el MVP completo.

## Qué significa cada métrica

| Métrica | Para qué sirve | Cómo interpretarla |
|---|---|---|
| Sesiones / visitantes | Ver uso del sistema | Visitante es un navegador identificado por cookie; no un alumno verificado. |
| Activas / cerradas / expiradas | Ver continuidad | Expirada = inactividad sin cierre confirmado; cerrada no significa consulta resuelta. |
| Mensajes | Revisar lo incorporado al historial | Texto de usuario/asistente, si se activó captura; no demuestra cada palabra escuchada. |
| Herramientas y operaciones | Saber qué hizo el agente | Inicio/fin, resultado técnico, duración y relación entre operaciones. No se guardan argumentos ni respuestas completas. |
| RAG / fuentes | Ver si encontró material | Cantidad e identificadores hash de fuentes. Encontrar fuentes no certifica que la respuesta sea correcta. |
| Cambios de agente | Revisar derivaciones | Excluye asignación inicial y repetición del mismo agente. |
| Interrupciones | Ver respuestas cortadas | Sobre respuestas completadas/interrumpidas; puede ser una interrupción legítima del usuario. |
| Errores reportados | Diagnosticar fallos explícitos | Cuenta eventos `error`. «Sesiones con errores» también incluye herramientas/operaciones fallidas y cuenta cada sesión una vez. |
| Uso y costo conocido | Estimar gasto | Tokens reportados y tarifas disponibles. Cobertura parcial = faltan usos o tarifas; no es factura ni costo total de infraestructura. |
| Tiempo en servidor | Ubicar demoras del agente | Inicio y duración de una respuesta en el servidor; no equivalen a latencia percibida. |
| Conexión → primera reproducción | Medir el arranque de voz en navegador | Una muestra válida por intento registrado. No mide cada turno posterior. |
| p50 / p95 | Ver experiencia habitual y demoras | Mediana y percentil 95 de las muestras disponibles; revisar cantidad/cobertura, especialmente con pocas pruebas. |
| Salud del registro | Detectar pérdida de telemetría | Confirmados, pendientes, descartados y fallos de escritura; último reporte por productor/sesión. Puede ser cobertura parcial. |

Una herramienta puede contener RAG o memoria: **no sumar sus duraciones/cantidades
como si fueran solicitudes independientes**. Costo desconocido no significa gratis;
latencia sin muestra no significa cero. No medimos todavía satisfacción, exactitud,
resolución de la consulta ni latencia completa por turno.

## Por qué aparecen `null` en el mensaje compartido

El contrato sirve para voz, herramientas y avatar. Cada evento usa solo una parte.
La vista técnica ahora muestra los campos disponibles y explica los ausentes en
«Campos sin dato y su significado». La base y la API conservan el contrato original.
Los `null` de mediciones dentro de `payload` se conservan visibles.

| Campo | Significado en ese `conversation_message` |
|---|---|
| `user_id` | Sin login institucional/Moodle; se usa `anonymous_id` de visitante. |
| `avatar_id`, `avatar_release` | Sesión de voz; no hay renderizador visual identificado ni versión de avatar. |
| `agent_id` | Limitación: este mensaje no se atribuye con certeza a Lira/Nexus/etc. El rol `assistant` no identifica al personaje. |
| `turn_id` | Limitación: aún no está enlazado a un turno de respuesta. `message_id` es la identidad del mensaje, no del turno. |
| `span_id`, `parent_span_id` | No es un tramo de herramienta instrumentado; las operaciones sí generan spans y padres cuando están anidadas. Un span raíz no necesita padre. |
| `tool_call_id` | Es un mensaje, no una ejecución de herramienta. |
| `request_id` | No se registró el identificador de solicitud del proveedor. No es igual al ID de mensaje. |
| `media_session_id`, `connection_attempt_id` | Correlación del navegador disponible en sus eventos de medios; no se enlaza aún a este mensaje del agente. |
| `release: unknown` | La sesión empezó sin versión configurada. Los lanzadores actuales envían el SHA Git; el historial no se reasigna al código nuevo. |

`source: agent` significa **productor Python**, no personaje. `trace_id` agrupa la
sesión; `app_session_id` identifica el arranque en la app; `conversation_id` la
conversación. `event_id` evita duplicar eventos; `payload.message_id` identifica
el mensaje del SDK. `room_name` y `participant_identity` enlazan el transporte.
`schema_version` identifica el contrato; `environment` separa local/UAM/producción.
`occurred_at` es la hora del productor y `received_at` la de recepción: su diferencia
no es la latencia de respuesta. La `Z` indica UTC: 18/oct 01:11 es 17/oct 20:11 en Colombia.

`text_available: true` significa que el texto está disponible en Conversación; se
omite de la vista JSON para no repetirlo. `interrupted` indica mensaje interrumpido;
`truncated` indica recorte al máximo permitido. `redaction: basic-v1` nombra las reglas
de ocultación. **No es anonimización completa**. Texto opt-in durante 7 días en esta
Mac, sin audio guardado por telemetría; UAM debe configurarlo explícitamente. Sesiones
anteriores sin captura no se pueden reconstruir. Mem0 tiene su propia persistencia.

El evento SDK expone el mensaje y su rol, pero no un campo dedicado de agente/turno
en la versión instalada. No asignamos el agente activo por hora porque un cambio de
agente puede preceder a la llegada del mensaje. Fuente: [eventos LiveKit](https://docs.livekit.io/reference/agents/events/).

## Prueba de Jacobo

Conservar primero cualquier trabajo sin publicar del servidor. No hacer `reset`,
`clean`, ni reemplazar `.env` o volúmenes. En un checkout limpio de pruebas, después
de `git fetch origin`, crear su rama desde `origin/backp-fase1`:

```sh
git switch -c feature/voice-validation origin/backp-fase1
python3 scripts/voice_demo.py init
# Completar .env.voice local: claves/modelo habilitados; nunca subirlo.
python3 scripts/voice_demo.py doctor
python3 scripts/voice_demo.py up
```

En Windows usar `python` en lugar de `python3`. Si ya existe esa rama, revisar sus
cambios antes de actualizarla. En UAM revisar primero procesos y puertos: la demo
no coordina automáticamente dos stacks. Detalle: [RUNBOOK.md](RUNBOOK.md).
Abrir `http://localhost:3500` en el equipo que ejecuta los servicios. Panel `/admin`:
usar **el valor** de `TELEMETRY_ADMIN_PASSWORD`, no el nombre de la variable.
Para texto, activar `TELEMETRY_CAPTURE_TRANSCRIPTS=true` en `.env.voice` y recrear
mediante `up` antes de empezar una sesión nueva. Usar datos ficticios.

Registrar por prueba: SHA de código, entorno, ID de sesión, resultado y fallo observable.

1. Hablar, oír respuesta e interrumpir; comprobar que la voz continúa.
2. Solicitar información que active cambio de agente y RAG; revisar las acciones reales.
3. Abrir «Ver eventos»: conversación nueva visible; correo ficticio ocultado como `[CORREO]`.
4. Ver uso/costo con cobertura explícita; no exigir costo completo si el proveedor no lo reporta.
5. Cerrar y reconectar: nueva sesión/intento, sin mezclar conversaciones.
6. Abrir dos sesiones independientes: sus mensajes, memoria y audio no deben cruzarse.

## Próximo paso

**Sí: retomar el avatar en paralelo con la aceptación de voz en UAM.** Santiago
continúa `feature/avatar-presentation` desde la base compartida; Jacobo valida voz;
Juan continúa correlación y métricas. No mantener dos arquitecturas divergentes.

Primero un avatar en una sesión: voz sincronizada, interrupción, vuelta a reposo y
fallback a voz si falla el renderer. Medir RAM y VRAM por separado, FPS y primera
imagen; después probar concurrencia con aislamiento de sesiones. La telemetría
pendiente incluye correlación mensaje → turno → reproducción y costo atribuible
por operación cuando exista evidencia. No bloquear la prueba de voz por esos faltantes.
