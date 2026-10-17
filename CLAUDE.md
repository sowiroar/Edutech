# Contexto vigente — 17 octubre 2026

Leer README.md y docs/mvp/README.md; este documento prevalece sobre instrucciones
históricas de ramas. Base compartida Edutech: backp-fase1. Voz de backup-fase-2
5e5abc3 incorporada sin migrar arquitectura. Trabajar por PR desde la base:
Juan feature/telemetry; Santiago feature/avatar-presentation; Jacobo
feature/voice-validation. Specs en docs/mvp, CI incluye PR a backp-fase1.

- Mantener LiveKit/Gemini, prompts/roles y RAG/Mem0. No copiar Pipecat/IPS de NeoIPS.
- Voz predeterminada; selector Voz/Avatar y telemetría todavía por implementar.
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
