# Panel y trazas de VIVA — 17 octubre 2026

Esta actualización amplía `feature/telemetry` (PR #8, base `backp-fase1`). No cambia
prompts, roles, frontend de voz ni assets. NeoIPS se consultó como referencia de
interfaz y observabilidad; no se importó Pipecat ni su arquitectura clínica.

## Qué cambió

- `/admin` usa una superficie clara inspirada en NeoIPS, con resumen, sesiones,
  herramientas, consumo, tiempos y salud. Solo esta ruta cambia de apariencia.
- «Ver eventos» abre un detalle al inicio del contenido y mueve el foco allí.
  Incluye Conversación, Herramientas y acciones, Todos los eventos, actualización
  explícita y paginación independiente por vista. Antes el detalle quedaba debajo
  de toda la lista, fuera de la vista; tampoco existía texto persistido.
- Herramientas y operaciones RAG/memoria: ejecuciones finalizadas, correctas,
  fallidas, canceladas, muestras de tiempo, p50/p95. No sumar herramientas y
  operaciones como si fueran llamadas independientes al modelo: pueden anidarse.
- Cambios de agente excluyen la asignación inicial y la repetición del mismo rol.
  Interrupciones tienen como denominador respuestas finalizadas/interrumpidas.
  Sesiones con errores tienen como denominador sesiones del periodo.
- Uso por proveedor/modelo/propósito/modalidad, entrada/salida/caché y estimación
  de costo parcial se mantienen. Reportes incompletos quedan explícitos.
- Salud usa el último snapshot por sesión/productor; no suma snapshots acumulados.
  La cobertura de salud puede ser parcial si el productor perdió su cola.
- Primera reproducción: un único audio por intento registrado de esa sesión.
  Duplicados, eventos huérfanos o sin tiempo se excluyen de percentiles y cobertura,
  y se muestran como excluidos. No se borran eventos históricos para corregir cifras.

## Transcripción autorizada, sin audio

El usuario autorizó texto con ocultación básica el 17 de octubre. Configuración:

```dotenv
TELEMETRY_CAPTURE_TRANSCRIPTS=true
TELEMETRY_TRANSCRIPT_RETENTION_DAYS=7
```

Activada únicamente en `.env.voice` local. Las plantillas quedan en `false`.
El agente y el colector deben compartir la activación; además el evento de inicio
de sesión debe registrar `transcript_capture=true`. Cambiar la variable requiere
recrear ambos servicios. No activa retrospectivamente sesiones antiguas ni UAM.

Se escucha `conversation_item_added` del SDK instalado, solo mensajes finales de
usuario/asistente, con identidad determinista por mensaje. No se registra cada
fragmento parcial, mensajes de sistema, audio, argumentos ni resultados de tools.
El texto se redacta **antes de encolarlo**, y nuevamente en el colector. Reglas
`basic-v1`: correos, URL, secuencias numéricas de teléfono/documento, algunos
secretos y formas explícitas de presentar el nombre. Máximo 4.000 caracteres.

**Esto no es anonimización completa:** nombres libres, direcciones escritas en
palabras, números dictados y datos sensibles no reconocidos pueden permanecer.
El acceso continúa siendo privado. No usar datos personales reales en las pruebas.
Las reglas se distribuyen en los dos paquetes con prueba de paridad para evitar
que versiones distintas se separen; no requieren un servicio externo ni modelo.

El texto vive exclusivamente en `telemetry_transcripts`, no en el JSON permanente
de eventos. Caduca desde la hora del evento (7 días por defecto; 1–30 configurables).
Las consultas lo ocultan inmediatamente al caducar; mantenimiento lo elimina cada
15 s cuando la base está disponible. Las copias de respaldo requieren su propia
política de retención. El evento técnico permanece con metadatos y «texto retirado».
No confundir esta política con la memoria Mem0, logs existentes o retención del
proveedor, que son sistemas separados y no se modifican en esta entrega.

El texto muestra lo incorporado al historial del SDK, **no certifica cada palabra
reproducida**. Las interrupciones se etiquetan. Las sesiones antiguas no contienen
texto recuperable; la interfaz lo explica, sin inventar una conversación.

## Trazabilidad y límites frente a NeoIPS

| Capacidad | Estado VIVA |
|---|---|
| Conversación ordenada por mensaje | Nuevas sesiones opt-in; texto redactado, sin audio |
| Tools / operaciones | Inicio/fin, estado, duración, rol de origen, call ID/turn ID cuando SDK los aporta |
| Relación entre ejecuciones | trace_id de sesión, span_id propio, parent_span_id de operaciones anidadas |
| RAG | Resultado disponible, número de fuentes e IDs hash estables; sin consultas, fragmentos ni rutas privadas |
| Consumo/costo | Ledger idempotente, deltas Live, tarifas versionadas, cobertura parcial |
| Respuesta → reproducción por turno | Pendiente; no confundir primera reproducción con latencia por turno |
| Resolución, satisfacción, intención/emoción | No medidas; no se deducen del cierre de la conexión |
| OTel / Langfuse | No implementados; los IDs locales no implican exportación OTel |
| FPS, VRAM, jitter, RTT del avatar | Contrato de medios preparado; instrumentación de renderer pendiente de Santiago |
| Usuario institucional / Moodle | Pendiente; visitante firmado no equivale a alumno autenticado |

Las fuentes RAG se identifican mediante SHA-256 truncado, no por nombres. Es útil
para comparar recuperaciones sin copiar documentos a telemetría. No mide la
relevancia de las fuentes ni demuestra respuesta fundamentada.

## Contrato y compatibilidad

`contracts/telemetry-event.v2.schema.json` es el contrato vigente y acepta los
sobres v1 existentes. v1 queda conservado como referencia publicada. Los eventos
nuevos `conversation_message`, `retrieval_completed`, `parent_span_id` y la captura
explícita requieren v2. El navegador sigue emitiendo medios v1; no puede enviar
mensajes de conversación a través de su API. Toda lectura requiere login privado.
La migración agrega tabla/índice sin alterar o borrar sesiones/ledger existentes.

`GET /api/admin/sessions/{id}/events?view=conversation|actions|all&cursor=UUID`
filtra en PostgreSQL, no solamente dentro de los 100 eventos cargados. Devuelve
contexto de sesión, autorización de captura, conteos y cursor. Cada página se ordena
cronológicamente en pantalla; «Cargar eventos anteriores» permite retroceder.
Los relojes de productores distintos pueden diferir; no se inventa una causalidad
por cercanía temporal. Los IDs correlacionan herramientas anidadas cuando existen.

La cola permanece acotada (512), lotes limitados por cantidad **y bytes** (200 KB
antes del sobre), reintentos acotados y sin persistencia en la ruta crítica de voz.
El navegador conserva el intento iniciado antes de recibir el token y separa
respuestas HTTP tardías entre sesiones. Solo cuenta audio adjunto al participante
agente, no cualquier elemento de audio de la página.

## Verificación y ejecución

```sh
python3 scripts/voice_demo.py up
# http://localhost:3500/admin — contraseña del valor TELEMETRY_ADMIN_PASSWORD en .env.voice
```

Hablar en la pantalla habitual; al terminar, abrir `/admin`, Actualizar, Ver eventos.
Conversación debe mostrar los nuevos mensajes, acciones los tools que realmente se
invocaron, y Todos los eventos el registro técnico. La voz no cambia de interfaz.
Probar correo ficticio `prueba@example.com`: debe verse `[CORREO]`. No usar secretos
reales para comprobar la ocultación.

Pruebas automatizadas: pytest agente, pytest colector con PostgreSQL **desechable
llamado `test`**, Node `--test tests/media-telemetry.test.cjs`, tsc y ESLint. Evidencia
actual en `docs/validation/2026-10-17-dashboard/README.md`. No truncar la base real.

Referencias revisadas: [eventos LiveKit](https://docs.livekit.io/reference/agents/events/),
[precios Gemini](https://ai.google.dev/gemini-api/docs/pricing) y, en NeoIPS,
`docs/19-informe-telemetria-portable.md`, `frontend/src/components/admin-panel.tsx`,
`frontend/src/components/trace-panel.tsx`, `frontend/src/app/globals.css`.

Para repetir la conversación sintética de integración (consume API autorizada):

```sh
uv run --project agent-starter-python python scripts/test_telemetry_runtime.py --live --scenario privacy --output docs/validation/2026-10-17-dashboard/runtime-privacy.json
```

El smoke de navegador `scripts/test_telemetry_dashboard.cjs` necesita Playwright
instalado en el entorno de pruebas (o `PLAYWRIGHT_MODULE` apuntando a su módulo).
Usa la sesión sintética anterior y credencial privada leída en memoria. No imprime
contraseñas ni texto del usuario. Produce capturas locales y `browser.json`.
