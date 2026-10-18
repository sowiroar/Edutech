## Campos de telemetría y base integrada — 17 octubre 2026, cierre

PR #8 ya fusionado en `backp-fase1` `3abca14`; CI de la base aprobado
(run 39086759054). El log antiguo de 15 errores Ruff no corresponde a esta base.
Nueva rama `feature/telemetry-field-clarity` desde esa base: detalle técnico
muestra campos disponibles y explica ausentes, conserva contrato/historial y
nulls de mediciones. Leer `docs/mvp/GUIA_METRICAS_EQUIPO.md`. No inventar agente,
turno ni costo por mensaje; aún falta correlación mensaje → turno → reproducción.
Jacobo puede probar voz/telemetría; UAM y renderer siguen sin validación nueva.
El frontend local se reconstruyó; backend, prompts, activos y datos sin cambios.

## Panel y texto opt-in — 17 octubre 2026 (vigente)

Leer `docs/mvp/TELEMETRY_DASHBOARD_Y_TRAZAS.md` desde la raíz del repo.
Usuario autorizó futuras transcripciones con ocultación básica, sin audio;
prevalece sobre la prohibición histórica de texto debajo. Contrato v2, compatible
con v1, texto separado con TTL (7 días local), captura desactivada por defecto.
No reconstruir sesiones antiguas. `/admin` claro como NeoIPS; voz visual intacta.
Pruebas PostgreSQL solo base `test`. No borrar datos reales. Sin despliegue UAM.

## Telemetría implementada — 17 octubre 2026, noche

Publicado por PR #8 https://github.com/sowiroar/Edutech/pull/8 contra
`backp-fase1` f072455, sin merge ni deploy. Rama activa `feature/telemetry`. Leer
`docs/mvp/TELEMETRY_IMPLEMENTACION.md` y `docs/validation/2026-10-17-telemetry/README.md`.
Colector PostgreSQL separado, cola acotada, contrato v1, ledger/tarifas versionadas,
visitante firmado y panel privado `/admin` implementados. `voice_demo.py up` genera
secretos faltantes en `.env.voice`; contraseña administrativa solo allí.
Voz predeterminada y prompts conservados; no modificar assets/roles ni presentar
Moodle, renderer o despliegue UAM como terminados. Costos parciales: no factura.
Uso Live por snapshot/delta, alias SDK Gemini→google. RAG/memoria con cobertura
explícita; Mem0 con hilos internos y embeddings sin usage no tienen costo completo.
Prueba real Lira→Nexus+RAG correcta; navegador con micrófono sintético, audio playing.
Postgres detenido: voz sigue; 12 fallos/6 descartes observados; base restaurada.
No confundir pruebas sintéticas habladas por Gemini con aceptación humana de voz.
Selector Voz/Avatar sigue siendo feature/avatar-presentation de Santiago.

# Contexto vigente — 17 octubre 2026

Leer README.md y docs/mvp/README.md; este documento prevalece sobre instrucciones
históricas de ramas. Base compartida Edutech: backp-fase1. Voz de backup-fase-2
5e5abc3 incorporada sin migrar arquitectura. Trabajar por PR desde la base:
Juan feature/telemetry; Santiago feature/avatar-presentation; Jacobo
feature/voice-validation. Specs en docs/mvp, CI incluye PR a backp-fase1.

- Mantener LiveKit/Gemini, prompts/roles y RAG/Mem0. No copiar Pipecat/IPS de NeoIPS.
- Voz predeterminada; selector Voz/Avatar pendiente. Telemetría: ver bloque vigente arriba.
- La falla del renderer no debe tumbar voz. No compartir video/audio de una sala
  con otra; validar lease antes de concurrencia Unreal.
- Identidad Moodle pendiente: separar visitante de usuario autenticado. No usar
  estudiante_uam como identificador único para métricas/memoria de todos.
- Sin datos de costo/latencia: null y cobertura. Medir reproducción en cliente
  aparte de generación. Sin credenciales no hay prueba de conversación real.
- Arranque local: python3 scripts/voice_demo.py init/doctor/up. Windows usa python.
  compose.voice.yml aislado, sin CUDA, sin deploy UAM; .env.voice fuera de Git.
- EDUTECH_SKIP_DEPLOY=1 al operar Git. No ejecutar scripts/setup o deploy sin
  revisar host/puertos/datos. Nunca reset/clean/force-push para "sincronizar".
- Assets en repo independiente Avatar, gitlink por SHA publicado y probado.
  No traer el bridge histórico VVA1 de archive al código de Gemini.
- Leer agent-starter-python/AGENTS.md antes de editar agente. uv y lock existentes.
- Medir RAM de proceso y VRAM por separado; Mac unificada no prueba Windows.
- No divulgar claves, tokens, DSN o credenciales VPN/RDP en evidencia.
- No afirmar deploy, autenticación, voz, seis mapas cocinados o UI probados por
  un simple catálogo/CI. Ver docs/mvp/VALIDACION.md.
