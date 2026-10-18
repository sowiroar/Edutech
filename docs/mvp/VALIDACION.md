# Validación de preparación — 17 octubre 2026

No equivale a aceptación del MVP ni prueba UAM. Ver la actualización de
configuración al final: hubo una prueba directa real de Gemini Live.

## Comprobado

- Fetch de ambos repositorios; fase1 es ancestro de fase2 (18 commits).
- Git worktree reparado tras organización; repos históricos y archivos locales conservados.
- Avatar: descarga LFS completa, fsck correcto, 13 entradas verificadas, 36 tests.
- Frontend de fase2: npm ci y build Next.js correctos con Node 24. El proyecto
  omite lint/typecheck en build por configuración previa: no son validaciones hechas.
- Agente antes de correcciones: 19 pruebas correctas, 15 hallazgos Ruff y seis
  archivos sin formato. Se corrigen imports/Any, formato y conservación de tareas
  de fondo; no se cambian prompts. Tres pruebas nuevas de retención/error/cancelación. Resultado final: 22 tests,
  Ruff y formato correctos. Knowledge-sync: 11 tests, Ruff y formato correctos.
- Perfil local: config Compose válido y dos pruebas del lanzador correctas.
- Motor OrbStack iniciado; LiveKit y Qdrant arrancados en proyecto aislado;
  HTTP LiveKit responde OK. Frontend y POST /api/token responden 200; un cliente
  RTC se conectó y desconectó con ese token. No se imprimió ni persistió el token.
  No se publicó micrófono ni se ejecutó un agente en esa prueba.
  Otros contenedores existentes no se modificaron.

## Bloqueo inicial (resuelto para configuración Google)

Al comienzo, el checkout no tenía .env/.env.local. Se creó .env.voice excluido de Git con
GOOGLE_API_KEY y GEMINI_LIVE_MODEL vacíos. Deben configurarse localmente; el doctor
los detecta sin imprimir valores. No se llamó a Google, no se midió voz conversacional,
RAG/Mem0 con proveedor ni gasto real. El ID histórico del modelo no se certifica.
No se accedió a UAM ni se ejecutó Unreal en esta preparación. No se reconstruyó
el paquete de seis avatares. No hay nuevo dato NVIDIA/RAM/VRAM/FPS.
Selector y telemetría son specs para las features, no funcionalidades ya entregadas.

## Reproducción

Ver RUNBOOK.md y ACEPTACION.md. Separar tests de código/configuración, conectividad
LiveKit y conversación de usuario. Registrar los resultados posteriores aquí o en
un informe fechado; nunca cambiar pendientes a exitosos sin ejecutar el ensayo.

Avatar PR #8 integrado en main a204705fca64f012b5c66c605ea34dc11ee3de43;
checks repository/tests/required aprobados. Edutech fija ese SHA para reproducción.

## Construcción y transporte local adicionales

Las tres imágenes de compose.voice.yml (voice-agent, knowledge-sync, frontend)
se construyeron correctamente en Docker arm64 de esta Mac, con Node 24. Frontend
Docker devuelve HTTP 200; POST /api/token 200 y conexión/desconexión RTC correctas.
No se publica micrófono ni hay inferencia en este ensayo. El inicializador de
volúmenes sale 0; escritura de índices RAG desde el usuario de la imagen comprobada.
El volumen de conocimiento también se inicializa con UID 10001, incluso si otro
contenedor lo creó antes; no se reutilizan datos/volúmenes de UAM.

La comprobación editor_mac.command check --avatar lira --profile efficient pasó
tras mover el workspace; no abrió el Editor. El bridge grabado se resuelve al
histórico y la nueva rama Avatar feature/avatar-presentation ya está publicada.

El frontend local puede abrirse en http://localhost:3500 mientras están activos
los servicios de prueba. El estado actualizado de configuración se registra abajo.
El resultado de CI se consulta en PR Edutech #5, no se infiere de pruebas locales.

## Actualización: configuración recibida de Jacobo y limpieza

- Google configurado en `.env.voice`, privado y excluido de Git; fuente fuera
  de los repos. Modelo `gemini-3.8-live` probado con una frase sintética directa:
  84002 bytes de audio, fin de turno confirmado. Sin grabación ni tokens guardados.
- `.env.example` y las plantillas de agente/frontend revisadas. Los secretos
  reales permanecen vacíos en las plantillas; devkey/secret son valores públicos
  del LiveKit de desarrollo. Ver CONFIGURACION.md para servicios usados por modo.
- Variables opcionales de portal conectadas al Compose local. Knowledge-sync
  completó 51 documentos UAM y 137 entradas de portal (77 privadas, solo título),
  índice de 188 registros/2608 fragmentos. No prueba la pertinencia de respuestas.
- Servicios locales iniciados con las imágenes arm64 ya construidas; sin tocar
  servicios ajenos ni UAM. El agente comienza precarga RAG/Mem0.
- Retirados dos worktrees temporales de septiembre, por solicitud del usuario,
  después de respaldar 250 y 216 archivos y verificar SHA-256 de cada archivo
  regular dentro de sus tar. Diffs y generador PDF conservados en archive local.
  No se incorporó su código experimental a Gemini. Antigravity global intacto.
- Dos tests del lanzador, Compose quiet y diff check correctos tras los cambios.

La prueba directa valida acceso al proveedor, no micrófono, conversación WebRTC,
handoffs, respuesta fundamentada, memoria útil ni sincronía del avatar.

## Fallo encontrado en el primer arranque con Google

La precarga RAG superó el límite de inicialización de 600 segundos del worker.
A las 23:05:53 UTC se cerró el proceso y comenzó a repetir OCR; se detuvo el agente
local para cortar el ciclo. La primera prueba del saludo obtuvo token HTTP 200 y
conexión RTC, pero cero audio y timeout: se conserva como fallo, no como aceptación.

El perfil local incorpora ahora `rag-init`, ejecutado antes del worker mediante
`service_completed_successfully`. Usa los dos constructores RAG originales y los
mismos volúmenes. Si alguno devuelve None, termina con error y bloquea el worker.
No cambia código del agente ni modelos. Revalidación nativa en curso; no inferir
que un Compose válido demuestra arranque completo ni voz.

## Revalidación después de separar la preparación RAG

`rag-init` terminó con salida 0: índices UAM y Nexus persistidos. El worker
cargó índices, inicializó Mem0 y se registró. Con la configuración reenviada por
Jacobo (mismos valores Google/portal), la prueba frontend token → LiveKit → saludo
Gemini → audio RTC pasó: HTTP 200, 250080 muestras recibidas a 48 kHz, 497 frames
no nulos, estados speaking → listening. No es prueba de micrófono ni handoffs.
El ensayo inicial fallido queda conservado; no se reconstruye su uso/costo a
partir del audio. La telemetría todavía no estaba implementada en este ensayo.
PR #7 integrado, CI completo aprobado, base f0724557d1a8dd8c81e9ac14b6d297cad2669590.

## Actualización final: telemetría P0

La telemetría ya está implementada en `feature/telemetry`. El estado anterior de
este informe describe la preparación histórica. Ver
[resultado reproducible](../validation/2026-10-17-telemetry/README.md) y
[implementación](TELEMETRY_IMPLEMENTACION.md): voz/handoff/RAG real, primer audio
Chromium y voz con Postgres detenido comprobados; 31 pruebas del agente, 14 del
colector con PostgreSQL y dos del lanzador. TypeScript y lint ejecutados aparte
del build. No prueba humana de micrófono, avatar, UAM ni costos completos.
