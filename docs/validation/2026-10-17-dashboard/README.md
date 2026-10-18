# Auditoría del dashboard y trazas — 17 octubre 2026

Cambios en `feature/telemetry`, continuación PR #8 hacia `backp-fase1`.
No merge ni despliegue UAM en esta validación. Pruebas locales Mac/Docker.

## Resultado observado

- 36 pruebas del agente; 21 del colector con PostgreSQL 17 desechable `test`;
  2 de instrumentación browser y 2 del lanzador. Ruff, TypeScript y ESLint correctos.
- Construcción Docker de agente, colector y frontend correcta. El build Next omite
  lint/types según configuración heredada; por eso se ejecutaron independientemente.
- `runtime-privacy.json`: conversación real Gemini desde cliente sintético, sin
  micrófono, cambio Lira → Nexus y RAG. Cuatro mensajes persistidos (usuario y
  asistente), correo ficticio redactado, spans presentes, 1.612.320 muestras de audio
  recibidas (no guardadas), 3.292 frames no nulos. Último snapshot 0 descartes/fallos.
- `browser-voice.json`: Chromium con micrófono sintético silencioso, audio `playing`,
  cero errores JS, ingest HTTP 200. Base confirma exactamente un inicio de conexión,
  un conectado y una primera reproducción, todos bajo el mismo intento.
- `browser.json`: detalle con foco, texto redactado, tools, eventos técnicos, retorno
  de foco, explicación de sesión antigua sin texto, filtros vacíos, logout y prueba
  de respuesta HTTP tardía que no restaura el panel privado. Cero errores JS y sin
  desbordamiento de página a 1440/390 px.
- `http-access.json`: login privado, cookie HttpOnly, rechazo anónimo/cross-origin,
  aislamiento visitante/sesión, imposibilidad de forjar identidad/uso/transcripción
  desde API browser, firma obligatoria, inicio obligatorio, filtros y logout.
- Revisión visual independiente: **ship**, ver design-review.md. No aceptación
  humana nueva ni certificación de avatar/GPU/NVIDIA.

## Casos de persistencia comprobados en base desechable

Deduplicación de UUID, aislamiento de contexto, costos/tarifa desconocida, expiración,
texto permitido solo con dos opt-in (servidor+sesión), redacción antes de almacenamiento,
texto ausente del JSON permanente, ocultación al vencer TTL y borrado, filtrado de
conversaciones aunque haya >100 eventos técnicos posteriores, paginación sin repetidos,
compatibilidad del sobre v1 con el esquema publicado, métricas de tools/handoffs,
salud por último snapshot y cobertura de reproducción sin duplicados/huérfanos.
Agente: límites de bytes con Unicode, cola saturada/transporte fallido, roles al
cancelar, spans anidados y ausencia de argumentos privados en eventos.

## Límites

La captura se habilitó solo en `.env.voice` local para futuras conversaciones. Las
anteriores no tienen texto recuperable. La ocultación básica no detecta todos los
identificadores; retención por defecto 7 días, sin audio. Se conserva Mem0 y los
logs del sistema existente, cuya política es independiente. No se borró la base real.

La prueba sintética no valida comprensión de un usuario real, exactitud médica,
reproducción perceptual, sincronía labial ni latencia por turno. Los costos son
estimaciones parciales por tarifa estándar, no factura. Herramientas y operaciones
anidadas no equivalen a llamadas adicionales al modelo. Las sesiones de esta prueba
se crearon desde checkout modificado y muestran release `unknown`; no se reescribió
su metadata histórica para atribuirles un commit posterior.

## Repetir

Ver `../../mvp/TELEMETRY_DASHBOARD_Y_TRAZAS.md`. `test_telemetry_runtime.py --live
--scenario privacy` consume API; usa texto ficticio, no datos personales. El smoke
browser requiere Playwright y la sesión sintética generada. PostgreSQL tests solo
con `TEST_DATABASE_URL` a base llamada `test`, nunca al volumen real.
