# Mirada de videollamada y continuidad del lector de audio

24 octubre 2026 · PR #11, `chore/avatar-latency-audit`. Sin despliegue UAM.

## Alcance confirmado

El usuario confirmó trabajar con los tres especialistas reales: **LIRA, NEXO,
ELIAN**. NOA/NOVA/ATLAS permanecen candidatos del visor; no se crean especialistas
ni se promocionan sus exportaciones por esta tarea.

## Ajuste de cámara y ojos

- La orientación importada de LIRA añadía aproximadamente 12,3° de perfil.
  `call-gaze.ts` calcula el frente a partir de los ejes ópticos de los ojos del
  GLB y corrige el conjunto completo una sola vez. No separa ropa, cabeza o pelo.
- La lente se coloca a la altura media real de los ojos tras normalizar el modelo.
  El encuadre mantiene los ojos aproximadamente al 72% de altura desde abajo,
  con margen superior y torso visible. Ya no se mira desde debajo del rostro.
- Después de la animación corporal, los dos ojos apuntan a la lente con una
  corrección máxima de 0,35 radianes (~20°). Se conservan gestos y parpadeos; se
  evita acumular rotación. Sin controles compatibles, se conserva el encuadre previo.
- Dos rotaciones de articulaciones por frame, sin texturas, mallas, render passes
  ni AudioContexts adicionales. No constituye una medición nueva de RAM/VRAM.
- Se verificaron visualmente LIRA, NEXO y ELIAN en el visor local. Los originales
  GLB y sus hashes permanecen intactos. La aprobación artística final es del equipo.

## Continuidad de audio

El analizador pasivo ahora pertenece al track remoto, no al perfil del rig.
LIRA → NEXO → ELIAN puede conservar el mismo lector cuando sigue el mismo track.
Al reemplazarlo se libera el anterior. Bloqueo de reproducción, mute, track
terminado o error de lectura llevan la boca a reposo sin detener el render.
Tras una pausa de render superior a 250 ms se descarta la pose acústica anterior.
La imagen temporal de una transferencia se captura con la boca en reposo.

Se conserva el estilo de Santiago: FFT2048 y dinámica de mandíbula original;
redondeo/extensión mantienen el suavizado sutil ya aprobado. La voz sale solo
por LiveKit. El analizador no añade una cola de reproducción ni duplica audio.

**Límite:** analizar PCM recibido no mide el instante físico del altavoz, ni
reconoce fonemas. `acoustic_onset_to_pose_max_ms` y `silence_to_rest_max_ms` son
medidas de la pose respecto al PCM. Un valor 0 significa la misma muestra/frame,
no latencia cero de red, modelo o dispositivo. No afirmar sincronía fonética perfecta.

## Validación reproducible

Desde `agent-starter-react`:

```sh
npm test
npm run lint
npx tsc --noEmit
```

Las pruebas de mirada verifican eje óptico, encuadre, movimientos de cabeza,
límite angular, ausencia de deriva y las tres jerarquías originales instaladas.
Las de audio cubren pausas, silencio, mute, bloqueo, track terminado, lectura
fallida y liberación idempotente. Los archivos privados ausentes se omiten
explícitamente en CI; las pruebas sintéticas siguen ejecutándose.

Para actualizar solo frontend local desde la raíz de Edutech:

```sh
python3 scripts/voice_demo.py web
```

Abrir `http://localhost:3500`, recargar tras terminar cualquier llamada anterior,
elegir Avatar e iniciar. LIRA recibe; pedir hablar con NEXO y luego ELIAN. Revisar
la mirada con chat abierto y cerrado, labios al hablar/silencio/interrupción,
transición sin boca congelada y eventos `avatar_quality_sample` con personaje y
hash correctos. No usar 3511 como sustituto de una llamada completa.

Pendiente de aceptación independiente: dispositivo de salida, micrófono/barge-in,
PC de Santiago/RTX4050, UAM y concurrencia. No extrapolar FPS del Mac a esos equipos.

## Primera validación local de esta revisión

69 pruebas frontend aprobadas; 3 omitidas por candidatos privados históricos.
Lint, TypeScript y compilación de producción aprobados. Se reconstruyó solo
el frontend local. La voz, el colector y los GLB no se reiniciaron/modificaron.

Una llamada posterior al cambio de mirada completó LIRA → NEXO → ELIAN con
respuestas de voz reales de Gemini Live, solicitudes escritas y micrófono
silenciado para la interacción. Hubo actividad acústica y cierre de boca
registrados para los tres, con atribución correcta a personaje/hash/sesión.
Evidencia sin texto ni audio: [live-call.json](live-call.json).

| Avatar | FPS medio de informes | Máximo cierre respecto a PCM | Primera imagen |
|---|---:|---:|---:|
| LIRA | 29,81 | 132,9 ms | 241,5 ms |
| NEXO | 30,05 | 133,3 ms | 141,5 ms |
| ELIAN | 29,96 | 100,2 ms | 131,9 ms |

La conexión de medios registró 345,3 ms; HTML `playing`, 582 ms desde el clic.
`playing` no mide primer sonido no silencioso. Se probaron encuadres de chat
abierto y cerrado; no promediar estos tamaños como un benchmark homogéneo.
Las tres últimas muestras estaban en `silent`. No se registró audio ni se
certificó barge-in con micrófono. Capturas locales en
`data/local-avatar/gaze-audit/` (ignoradas por Git).

## Cierre local después de revisar subtítulos

Se corrigió también la entrada de los especialistas: sus indicaciones iniciales
ahora forman parte del contexto de sistema. La prueba completa y el motivo
están en [SUBTITULOS_TRANSFERENCIAS.md](SUBTITULOS_TRANSFERENCIAS.md). El worker
local sí se reconstruyó en este cierre, después de la primera validación anterior.
No se cambiaron modelos, voces, herramientas, fuentes ni GLB.

Llamada final LIRA → NEXO → ELIAN → NEXO: los especialistas respondieron a la
pregunta pendiente sin pedir repetirla, los subtítulos no mostraron los prefijos
internos detectados antes y la sesión cerró correctamente, sin eventos de error.
53 tests Python y Ruff aprobados. [Evidencia final](final-call.json), sin texto
ni audio; los valores son del Mac local, no del servidor UAM.

| Avatar | FPS medio de informes | Máximo cierre respecto a PCM |
|---|---:|---:|
| LIRA | 29,62 | 102,0 ms |
| NEXO | 30,11 | 142,1 ms |
| ELIAN | 30,02 | 107,8 ms |

Las tres últimas muestras estaban en silencio. NEXO tuvo dos períodos activos
por la transferencia de regreso. Chat abierto/cerrado cambió el tamaño del
canvas: no presentar la tabla como benchmark homogéneo de carga. Consumo real
medido por separado: [CONSUMO_ACTUAL.md](CONSUMO_ACTUAL.md). Sigue pendiente
aceptación con micrófono físico, equipos de Santiago/UAM y concurrencia.
