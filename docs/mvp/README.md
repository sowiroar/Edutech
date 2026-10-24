# Guías vigentes de Edutech

Estado del **21 de octubre de 2026**. Base de desarrollo: `main`. Una arquitectura
LiveKit + Gemini Live, con presentación Voz/Avatar y telemetría común.

## Recorrido disponible

El frontend dibuja **LIRA de Juan, NEXO y ELIAN en WebGL**, sin mantener Unreal activo.
LIRA/Aoede recibe; Nexus/NEXO/Puck y ELIAN/Kore aparecen al transferir. Los demás
personajes todavía no tienen clases de agente implementadas en este worker.
Las pruebas locales comprobaron audio y cambio de avatar con entrada sintética.
No equivalen a aceptación estética, lip sync fonético, UAM o concurrencia.

## Documentación

| Necesidad | Guía |
|---|---|
| Iniciar servicios y aplicación | [README del repositorio](../../README.md) |
| Trabajar con el visor y exportar | [AVATAR_WEB.md](AVATAR_WEB.md) |
| Instalar modelos en otro equipo | [Modelos web](../../agent-starter-react/public/avatars/README.md) |
| Evitar confundir LIRA o las voces | [AVATAR_AGENT_MAPPING.md](AVATAR_AGENT_MAPPING.md) |
| Labios, materiales y ELIAN en llamada | [Verificación de los tres agentes](../validation/2026-10-21-avatar-speech-style/README.md) |
| Acabado de NEXO y fondo común | [Actualización visual](../validation/2026-10-21-nexo-quality/README.md) |
| Reparación vigente de NEXO | [Voz, transferencias y rostro nativo](../validation/2026-10-21-nexo-repair/README.md) |
| Respuestas y piel mate de NEXO | [Latencia y alcance de la medición](../validation/2026-10-21-nexo-latency/README.md) |
| LIRA no entra o la llamada se desconecta | [Arranque y reintento verificados](../validation/2026-10-21-lira-startup/README.md) |
| RAM, memoria gráfica, CPU y FPS | [Medición del 21 de octubre](../validation/2026-10-21-avatar-resources/README.md) |
| Preparar la publicación | [Entrega web](ENTREGA_WEB_2026-10-21.md) |
| Ramas y coordinación | [FLUJO.md](FLUJO.md) |
| Configuración y operación | [CONFIGURACION.md](CONFIGURACION.md), [RUNBOOK.md](RUNBOOK.md) |
| Telemetría y panel | [Implementación](TELEMETRY_IMPLEMENTACION.md), [dashboard](TELEMETRY_DASHBOARD_Y_TRAZAS.md) |
| Interpretar las métricas | [Guía del equipo](GUIA_METRICAS_EQUIPO.md) |
| Alcance de las pruebas | [VALIDACION.md](VALIDACION.md), [ACEPTACION.md](ACEPTACION.md) |

Las especificaciones [de presentación](SPEC_AVATAR_PRESENTATION.md) y
[telemetría](SPEC_TELEMETRY.md) conservan requisitos y antecedentes.
El recorrido Unreal/bridge de [AVATAR_LOCAL_WINDOWS.md](AVATAR_LOCAL_WINDOWS.md)
es histórico; no es necesario para el frontend web vigente. Los resultados
fechados de la demo del 20 de octubre no sustituyen la evidencia nueva.

Moodle/SSO, agentes y modelos web de ATLAS/NOVA/NOA, correlación completa de costos,
sincronía fonética y validación de varias sesiones siguen siendo trabajos separados.
