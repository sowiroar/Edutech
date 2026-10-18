# Edutech · VIVAVerse UAM

Base de integración: **backp-fase1**. Incluye la voz de Jacobo de backup-fase-2.
Agentes LiveKit + Gemini Live, frontend Next.js y opción Unreal en desarrollo.

## Empezar

- [Guía del MVP y estado](docs/mvp/README.md).
- [Arranque Mac/Windows y pruebas UAM](docs/mvp/RUNBOOK.md).
- [Ramas, responsables y entrega](docs/mvp/FLUJO.md).
- Juan: [telemetría implementada y panel privado](docs/mvp/TELEMETRY_IMPLEMENTACION.md).
- Santiago: [feature/avatar-presentation](docs/mvp/SPEC_AVATAR_PRESENTATION.md).
- [Pruebas realizadas](docs/mvp/VALIDACION.md) y [aceptación pendiente](docs/mvp/ACEPTACION.md).

Desde esta carpeta, Python 3 y motor Docker activo:

```sh
python3 scripts/voice_demo.py init
# Completar .env.voice localmente: GOOGLE_API_KEY y GEMINI_LIVE_MODEL.
python3 scripts/voice_demo.py doctor
python3 scripts/voice_demo.py up
```

Frontend: http://localhost:3500. Windows: usar `python` en lugar de `python3`.
Este arranque no usa NVIDIA; Gemini necesita conexión y credenciales válidas.
El render Unreal es otra carga, que sí necesita aceleración gráfica para ser útil.

El Compose histórico y la [guía anterior](docs/history/README-pre-20261017.md)
se conservan para trazabilidad/UAM; no son instrucciones del perfil local de voz.
No ejecutar despliegue automático al hacer pull. Usar EDUTECH_SKIP_DEPLOY=1.

## Repositorio

| Ruta | Responsabilidad |
|---|---|
| agent-starter-python | Agentes, herramientas, RAG y memoria |
| agent-starter-react | Frontend y emisión de tokens LiveKit de demo |
| avatar-bridge / avatar-render | Integración histórica Gemini → Unreal → MJPEG |
| Avatar | Submódulo: SHA exacto del repositorio de assets |
| knowledge-sync / data | Sincronización/documentos institucionales |
| telemetry-service / contracts | Colector PostgreSQL, contrato y costos con cobertura |
| compose.voice.yml | Entorno local de voz y telemetría aislado |
| docs/mvp | Specs, runbook, pruebas y flujo actual |

El checkout externo hermano Avatar es para edición; inicializar el submódulo
solo cuando haga falta reproducir un build desde Edutech. No copiar .env ni assets
manualmente entre ramas. Seis personajes visuales no implican seis roles nuevos.

Estado: voz real y telemetría probadas localmente. Panel en http://localhost:3500/admin;
contraseña TELEMETRY_ADMIN_PASSWORD en .env.voice. Selector/avatar y validación UAM
siguen pendientes. No afirmar MVP institucional completo ni SSO.
