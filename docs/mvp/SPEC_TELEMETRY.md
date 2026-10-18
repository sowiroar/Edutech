# Especificación: feature/telemetry — Juan

Estado: P0 implementado en feature/telemetry; implementación y límites verificables
en TELEMETRY_IMPLEMENTACION.md y docs/validation/2026-10-17-telemetry/.
Este documento conserva los criterios de aceptación, no amplía la evidencia real.
Referencia aportada: informe NeoIPS del 17-oct-2026, commit b3cf60b. Se reutiliza
su diseño de eventos/contexto/emisor/adaptadores, no su código sin disponer de él,
ni versiones, tarifas, Pipecat, Simli, dominio clínico o datos privados.

## Objetivo P0 del martes

Una llamada real de voz queda correlacionada con usuario conocido o visitante,
sesión, agente, modelo, errores y consumo disponible. Panel privado mínimo con
rango temporal, sesiones, latencias, tokens por modalidad, costos estimados y
cobertura. La misma instrumentación servirá al modo Avatar.

## Integración real de destino (diagnóstico previo)

- Entrypoint: agent-starter-python/src/agent.py, multiagent_session y AgentSession.
- Gemini es audio bidireccional: NO inventar etapas STT/TTS ni sumar sus precios.
- Hook existente user_input_transcribed; anunciar_personaje_avatar publica
  avatar.character. Instrumentar herramientas/handoffs sin cambiar prompts.
- RAG y Mem0 también llaman modelos/embeddings: registrar propósito independiente;
  medir cobertura de estas llamadas, no asumir que el uso de la sesión los incluye.
- app/api/token/route.ts emite identidad/sala aleatorias de espacio reducido, sin
  identidad Moodle validada. _resolver_user_id tiene fallback estudiante_uam.
  No usar ese fallback como usuario único ni mezclar memorias de visitantes.
- Revisión de API de hooks sobre la versión realmente instalada: eventos de uso
  de sesión o métricas realtime según SDK; escoger UNA fuente contable por consumo.
  La documentación reciente puede diferir de uv.lock. Añadir prueba contra el tipo instalado.

## Hooks comprobados en la instalación local

uv.lock instala livekit-agents 1.8.2. Su voice/events.py declara
SessionUsageUpdatedEvent.usage (AgentSessionUsage); metrics_collected de sesión
está deprecado para contabilidad, mientras métricas de latencia están en
ChatMessage.metrics. Implementar el ledger desde session_usage_updated y comprobar
si cada campo recibido es snapshot o delta; la versión del proveedor sigue siendo
la autoridad. No contar además métricas del plugin como otro gasto.

## Contrato v1 implementado (compartido con Santiago)

Fuente generada: `contracts/telemetry-event.v1.schema.json`; sobre validado y versionado:

| Campo | Regla |
|---|---|
| schema_version, event_id | 1; UUID, idempotencia de entrega |
| occurred_at, received_at | UTC productor y receptor; no equivalen a reloj sincronizado |
| source | agent / browser / bridge / renderer; collector solo para expiración |
| environment, release | local/test/uam-demo; SHA del backend y avatar cuando aplique |
| conversation_id, app_session_id | UUID del servidor; relación estable con la sala |
| user_id, anonymous_id, identity_source | user_id nullable; visitante separado; identidad Moodle solo verificada en servidor |
| turn_id, request_id, tool_call_id | nullable cuando no existe correlación fiable; nunca adivinar por texto |
| media_session_id, connection_attempt_id | IDs por conexión/intento |
| agent_id, avatar_id | rol lógico separado del diseño; no convertir seis diseños en seis roles |
| presentation_mode | voice / avatar; independiente de channel=voice |
| type, payload | catálogo y payload específico, límites de tamaño y sin secretos |
| trace_id, span_id | opcionales; no prueba exportación exitosa |

Eventos P0: session_started, session_ended, agent_changed, response_started,
response_completed, response_interrupted, tool_started, tool_completed,
usage_recorded y error. Incluir cierre inesperado/expirado; start no se infiere de
una respuesta. session_started debe persistir antes de aceptar eventos asociados.
No afirmar respuesta reproducida por haber emitido response_completed.

Eventos de Santiago: media_connect_started, media_connected, audio_playback_started,
video_first_frame, media_stalled, media_recovered, presentation_changed,
avatar_unavailable, media_quality_sample. Se acuerdan en el mismo schema y helper;
no se requiere implementarlos todos para cerrar la entrega P0 de voz.

## Identidad y acceso

Para la demo sin Moodle: visitante con ID opaco emitido en servidor; distinguir
visitas/sesiones de estudiantes autenticados. IDs UUID amplían el espacio actual.
Jacobo/Mario resuelven el contrato de identidad de Moodle; no confiar en user_id
arbitrario recibido por POST. No afirmar SSO, RBAC institucional ni multitenancy.
Panel protegido por sesión administrativa del servidor, sin secreto en NEXT_PUBLIC.
API de cliente ligada a sesión/participante autorizado, allowlist de eventos,
rate limit/tamaño y deduplicación. El cliente no puede emitir costos ni elegir
usuario/tenant ajeno. Transcripciones optativas y redactadas, sin audio crudo por
defecto. La emoción inferida no es satisfacción ni diagnóstico.

## Persistencia y contabilidad

Propuesta P0: PostgreSQL para telemetría, separado de SQLite de conocimiento y
Qdrant de Mem0. Añadir servicio opcional de desarrollo y migrador transaccional;
no requiere pgvector. Si la infra UAM ya ofrece Postgres, reutilizar esquema aislado.
Tablas mínimas: telemetry_sessions, telemetry_events, usage_ledger y pricing_rates.
Indexes por (session, received_at), (environment, timestamp) y clave dedup.
Cola acotada, lote y timeout fuera del camino crítico; contadores enqueued,
persisted, dropped, write_failed y queue_age, visibles aun si falla Postgres.
No prometer entrega exactamente una vez ni cero pérdidas con cola en memoria.

Ledger: provider/model/request/purpose/attempt, unidad, cantidad, modalidad,
source=provider|derived, rate_id, cost_usd nullable y cost_status.
Propósitos: conversation, rag, memory, embedding; derivados no se suman a su
fuente. Si el SDK entrega acumulados, calcular deltas con manejo de reinicio;
no sumar snapshots de toda la sesión como llamadas distintas.
Tarifas por proveedor/modelo/unidad/fecha/moneda, verificadas al implementarlas.
No copiar 0,30/2,50 del informe. Ausencia de tarifa/uso: null + cobertura.
Reintento/fallo también consume si el proveedor reporta uso. Total conocido no
es factura final; infraestructura, red/TURN y GPU se informan separados.

## Latencias y dashboard

- server_response_start_ms: límites de eventos y reloj monotónico documentados.
- browser_first_audio_ms: desde intento local hasta reproducción real; no confundir
  con latencia de respuesta por turno.
- turn_to_playback_ms: solo si marcadores de turno y reloj permiten medirlo; si no,
  pendiente/null. No restar timestamp de Mac y UAM sin compensación.
- p50/p95 por definición, modo y periodo, con n y cobertura; no promediar percentiles.
- API propuesta: GET /api/admin/metrics?from=&to=&mode=, GET /api/admin/sessions,
  GET /api/admin/sessions/{id}/events?cursor=; POST /api/telemetry/media para browser.
  Paginación y auth obligatorias; agregación determinista SQL, no un LLM para sumar.
- Panel /admin: totales, errores, sesiones recientes, latencias, uso por modelo y
  propósito, costos conocidos y cobertura. Polling inicial suficiente; OTel/OTLP
  opcional P1 y sin bloquear la demo.

## Pruebas de aceptación

1. Voz y avatar comparten session/conversation; modos diferenciados y sin doble registro.
2. Dos visitantes y un handoff no mezclan identidad, memoria ni turnos.
3. Evento repetido no duplica fila; snapshot repetido no duplica consumo.
4. Costo sintético con tarifa de prueba coincide; costo desconocido sigue null.
5. Error de base no bloquea conversación y deja señal operativa de pérdida.
6. Fallo/reintento/cancelación se asocian al turno correcto, incluidos eventos tardíos.
7. Usuario no autorizado no lee admin ni cambia UUID para leer otra sesión.
8. Logs/exportaciones no contienen claves, tokens, correo/documento de pruebas.
9. Consulta con periodo no mezcla demo y producción; KPI permite rastrear eventos.
10. Una llamada real breve, consentida para prueba, acredita productor; fixtures no
    se presentan como gasto real. Para mostrar datos sintéticos, rotularlos.

Fuentes técnicas a consultar durante implementación:
- https://docs.livekit.io/testing/observability/data/
- https://docs.livekit.io/reference/agents/events/
- https://docs.livekit.io/reference/recipes/metrics_realtime/

## Matriz de cierre P0 — evidencia de esta entrega

| Criterio | Resultado y límite |
|---|---|
| Contexto común voz/avatar | Contrato y modo implementados; voz probada. Selector y renderer real pendientes de Santiago. |
| Visitantes y handoff | Identidad aislada HTTP/unitaria, Lira→Nexus real por texto sintético. Memoria pedagógica multiusuario no aceptada. |
| Idempotencia/snapshots | Pruebas PostgreSQL y SDK instalado correctas. |
| Costos conocidos/desconocidos | Decimal, tarifas fechadas y null probados; subtotal real disponible, cobertura parcial explícita. |
| Caída de base | Saludo real completo con Postgres detenido; pérdidas visibles; base recuperada. |
| Cancelación y eventos tardíos | Prueba automatizada de origen/turno y cierre acotado; interrupción humana pendiente. |
| Acceso y aislamiento | Panel privado, firmas, rechazo de UUID/consumo/origen ajenos y logout comprobados. |
| Datos excluidos | Contrato sin texto/audio, evidencia sin secretos; Mem0/logs previos tienen políticas propias. |
| Filtros y trazabilidad | SQL por entorno/modo/periodo, detalle paginado y cobertura de latencias implementados. |
| Proveedor real | Gemini Live, RAG y reproducción Chromium con micrófono sintético probados; no aceptación humana ni UAM. |

P0 de instrumentación de voz queda implementado. No declarar terminadas las pruebas
de avatar, identidad Moodle, costos totales Mem0/bootstrap ni telemetría de GPU.
Estos límites no se resuelven reemplazando valores ausentes por cero.
