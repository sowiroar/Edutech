> Flujo vigente: crear una feature nueva desde origin/main y abrir PR a main.
> Los nombres de ramas en el alcance histórico no implican que sigan abiertas.

# Especificación: feature/avatar-presentation — Santiago

Estado: trabajo por implementar sobre backp-fase1 consolidada. No migrar la
arquitectura agente ni reemplazar el frontend de Jacobo completo.

## Interfaz y contrato compartido

Dos botones visibles antes de conectar: **Voz** (predeterminado) y **Avatar**.
La selección cambia presentation_mode, no el agente, identidad o conocimiento.
Para P0, bloquear el cambio durante una llamada y permitirlo al terminar; así no
se añade una reconexión ambigua en medio de un turno. Evolución en vivo posterior.
Si Avatar está ocupado/no disponible, mostrar motivo y opción explícita de Voz.
No mostrar un botón Avatar que asegure disponibilidad solo por responder HTTP.

Reutilizar SpeakingAnimation para Voz y AvatarStage/endpoint existente como base
para Avatar. Mantener chat, controles, micrófono y misma sesión. Un solo audio
reproducido: documentar qué ruta se oye en cada modo y probar ausencia de eco.
MCP es desarrollo, nunca transporte de audio de usuarios.

Coordinar con Juan app/api/token/route.ts: selección de modo y reserva de renderer
junto con IDs de sesión; no duplicar token endpoint, inventar otro user_id ni
cambiar auth desde frontend. Emitir eventos del contrato SPEC_TELEMETRY.md.

## Hallazgo crítico de concurrencia

Inspeccionar RoomFollower/puente antes de habilitar varias sesiones: el renderer
actual y el stream MJPEG son recursos compartidos. No debe verse/oirse una sala
ajena. P0: un lease explícito por renderer, segunda llamada rechazada o derivada
a Voz; no prometer un proceso por usuario sin medir VRAM y costo.
El MJPEG histórico está a 854x480 / 12 fps por configuración; 2 fps reportados
por Jacobo no prueban dónde está el cuello de botella.

## Seis diseños

Catálogo de Avatar: nexo-design, lira, elian-design, noa-design, nova-design,
atlas-design. Mantener legacy, no borrar assets históricos. Los tags/roles actuales
no cambian automáticamente al elegir un mapa nuevo. Verificar receptor, live link,
identidad, cuerpo/ropa/accesorios y cámara frontal de cada escena.
La app cocinada Mac de octubre 12 contiene solo Lira/Elian/Noa y WAV local.
Elan/Noa/Lira aprobadas no se rediseñan; Noa mantiene SK_Noa_AlternateFace.
Mapas nuevos no se habilitan en un paquete hasta cook de todas sus dependencias.

## Orden de diagnóstico

1. Paquete nativo con un solo avatar, sin Editor: FPS CPU/GPU y memoria en reposo/habla.
2. Audio local/cancelación: primera muestra, backlog y retorno a reposo.
3. Captura/codificación: tiempo y FPS producidos, resolución real, CPU y GPU.
4. Transporte: bytes/s, RTT y frames recibidos; distinguir VPN de LAN.
5. Navegador: frames visibles, estancamiento y audio reproducido.

No inferir FPS MJPEG con getStats de una pista WebRTC que no transporta ese video.
Para MJPEG, medir frames/captura en servidor y definir instrumentación cliente
compatible; para WebRTC usar deltas de stats de la pista correcta. Nunca inferir
sincronía labial por audio ACK/FPS. Ensayo visual separado.

## Equipo de Santiago y UAM

Santiago: portátil Ryzen 7 reportado de 6 núcleos, 16 GB RAM, RTX 4050 laptop;
VRAM/driver/TGP reales por medir, no inferirlos del nombre. Priorizar un renderer,
720p/30 fps objetivo inicial, sin Editor mientras se mide la aplicación. No levantar
Ollama/Whisper/Kokoro CUDA con el recorrido Gemini si no se usan.
UAM: cifras RAM/GPU dadas en conversaciones son reportadas, confirmar hardware
antes de fijar capacidad. 128 GB RAM no sustituyen VRAM discreta.

En Windows (PowerShell), guardar CSV local de GPU durante prueba:

```powershell
nvidia-smi --query-gpu=timestamp,name,memory.total,memory.used,utilization.gpu --format=csv -l 1 > gpu.csv
# Ctrl+C al terminar. En otra consola, sustituir PID real:
Get-Process -Id 1234 | Select-Object Id,ProcessName,WorkingSet64,PrivateMemorySize64
```

VRAM global incluye otros procesos; en WDDM memoria por proceso puede ser N/A.
No convertir N/A en cero. WorkingSet, Private Bytes y VRAM son magnitudes distintas.
Registrar SHA de ambos repos, build, escena, resolución, perfil, driver, duración,
repeticiones, pico/reposo y procesos concurrentes. Mac usa memoria unificada y no
es comparación directa con VRAM NVIDIA. Empezar con 1 sesión antes de 2/4 usuarios.

## Aceptación

- Voz sigue funcionando con bridge/render apagados y muestra alternativa clara.
- Avatar: cámara frontal, una geometría corporal correcta, pelo/ropa/rostro íntegros.
- Tres respuestas, una interrupción, desconexión/reconexión y reposo sin eco.
- Segunda sesión no roba renderer ni recibe contenido de la primera.
- Métricas reportadas con units/clock/source; no éxito de audio por mero envío.
- Empaquetado Windows/Linux probado en destino; Mac no se copia como ejecutable UAM.
- PR con evidencia, límites y pin de Avatar. El martes se activa solo si pasa;
  nunca sacrificar voz para ocultar un fallo de avatar.
