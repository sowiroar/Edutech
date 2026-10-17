# Base compartida para la muestra del 20 de octubre de 2026

Decisión del 17 de octubre: una arquitectura LiveKit + Gemini Live, un frontend
con presentaciones Voz / Avatar y una telemetría común. La voz de Jacobo es el
recorrido base; la presentación Unreal se integra de forma optativa. No se cambia
el framework a Pipecat ni se copian los prompts/dominio médico de NeoIPS.

## Estado de partida comprobado

- `origin/backp-fase1`: f1ccd3c; `origin/backup-fase-2`: 5e5abc3, 18 commits encima.
- Fase 2 ya contiene la historia del MJPEG, pero su tile usa SpeakingAnimation.
  Fusionar historias no habilita automáticamente la salida Unreal.
- La infraestructura de voz local nueva es `compose.voice.yml`, aislada de la
  composición histórica de UAM. Scripts de despliegue antiguos no son el arranque local.
- Telemetría, autenticación Moodle y selector Voz / Avatar son entregables
  especificados, todavía no implementados por esta preparación.
- Avatar tiene seis diseños prioritarios; no equivale a seis agentes de backend.
- Ver [VALIDACION.md](VALIDACION.md) para pruebas ejecutadas y bloqueos actuales.

## Documentos de trabajo

1. [FLUJO.md](FLUJO.md): ramas, propiedad de archivos y entrega a Jacobo.
2. [RUNBOOK.md](RUNBOOK.md): Mac, Windows, UAM y verificaciones.
3. [SPEC_TELEMETRY.md](SPEC_TELEMETRY.md): Juan, `feature/telemetry`.
4. [SPEC_AVATAR_PRESENTATION.md](SPEC_AVATAR_PRESENTATION.md): Santiago.
5. [ACEPTACION.md](ACEPTACION.md): demostración, pruebas y evidencia.

## Prioridad hasta el martes

P0: reproducir la voz real y registrar sesiones/consumo/errores de forma fiable.
P0: panel mínimo con filtros y cobertura, sin presentar desconocidos como cero.
P1: activar avatar opcional sin perder voz ni aislamiento de sesiones.
P1: medir NVIDIA y decidir el recorrido que se demostrará; conservar voz como respaldo.
P2: capacidades avanzadas de OTel, calidad evaluada y optimización concurrente.
No prometer SSO Moodle, seis roles nuevos, resolución de casos o escalabilidad ya validada.

El resumen de Mario define identidad Moodle como pendiente. Las referencias de
memoria de avatares son del proceso completo y no miden VRAM NVIDIA por avatar.
