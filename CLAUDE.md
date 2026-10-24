# Continuidad de Edutech

Leer [AGENTS.md](AGENTS.md), [README.md](README.md) y el
[índice vigente](docs/mvp/README.md). AGENTS.md es la fuente única de
instrucciones de trabajo; no duplicar estados históricos aquí.

El recorrido actual usa LIRA de Juan, NEXO y ELIAN en el navegador, LiveKit y Gemini
Live. La autoría Unreal y la distribución privada de modelos se documentan
por separado. Las pruebas locales no certifican UAM, SSO ni lip sync fonético.

Continuación del 22 de octubre: [auditoría y pruebas de latencia](docs/validation/2026-10-22-avatar-audit/README.md)
y [exportación Windows/Mac](docs/mvp/AVATAR_WEB.md). Mantener pendientes las
revisiones de cualquier GLB recién generado.

23 octubre: [LIRA exportada con sus cejas originales](docs/validation/2026-10-23-lira-export/README.md).
La vista previa está disponible; la promoción a llamadas sigue pendiente.

Entrega vigente: [GLB de Santiago, audio y métricas de llamadas](docs/validation/2026-10-23-santiago-integration/README.md). Los candidatos Mac se conservan como históricos; el visor y las llamadas usan ahora los GLB originales recibidos.

## Preferencia visual vigente: movimiento de Santiago

23 octubre, después de las pruebas de articulación: el usuario prefirió la
animación anterior. Rig y algoritmo acústico restaurados desde 0225f0a; FFT2048.
Se mantienen rendimiento adaptativo y telemetría. El clasificador experimental
no está activo. Ver docs/validation/2026-10-23-santiago-motion-restore/README.md.
No reutilizar mediciones previas de cierre como si fueran de esta restauración.

## Pulido solicitado sobre el estilo conservado

23 octubre: el usuario confirmó «Sí, conservar este estilo y pulirlo».
Se mantiene la base Santiago y se suavizan únicamente redondeo/extensión a 55 ms;
mandíbula, rangos y cierre iguales. El visor compara `smooth` con `santiago`.
Ver docs/validation/2026-10-23-subtle-lip-polish/README.md. No reintroducir el
clasificador experimental ni sustituir la identidad de los modelos.

23 octubre: catálogo de seis IDs y transición con imagen temporal, un único
modelo WebGL activo. Entrega web revisada: LIRA/NEXO/ELIAN; NOA/NOVA/ATLAS no
están en el paquete GLB recibido. No confundir catálogo, exportación y agente.
Estado, límites y pruebas: docs/validation/2026-10-23-family-transitions/README.md.


24 octubre — NOA/NOVA/ATLAS GLB generados, solo preview. Primera apariencia
rechazada por el usuario; se repararon textura virtual, slots por sección y
superficies procedurales, pero NO hay aceptación visual/de voz. No promoverlos
por pasar tests. Los tres GLB originales de Santiago siguen intactos en llamadas.
Ver docs/validation/2026-10-23-family-transitions/README.md y candidate-models.json.
El GLB nuevo depende de family-materials.ts para conservar cejas/trazos/ropa/barba.


## 24 octubre — tres agentes, mirada a cámara y audio continuo

El usuario confirmó limitar las llamadas a LIRA/NEXO/ELIAN. NOA/NOVA/ATLAS
continúan como candidatos, sin especialistas nuevos. Se corrige el perfil
importado, cámara a altura de ojos y seguimiento acotado de la lente mediante
call-gaze.ts. No modificar GLB ni rig labial por este ajuste. El lector de audio
pertenece al track remoto, sobrevive al cambio de rig y vuelve a reposo ante
reproducción detenida o errores. Conservar el estilo Santiago. Ver
docs/validation/2026-10-24-call-gaze/README.md para pruebas y límites; no
afirmar latencia cero, sincronía fonética ni aceptación UAM.

24 octubre, consumo real: docs/validation/2026-10-24-call-gaze/CONSUMO_ACTUAL.md.
Una pestaña de llamada: 263–272 MiB RSS medio, pico observado 326 MiB; Docker
~1,9 GiB con otra llamada existente. No extrapolar a VRAM ni concurrencia UAM.
Cierre local: el prefijo interno de subtítulos se reprodujo con RoomIO y se
corrigió trasladando las mismas indicaciones de entrada al contexto de sistema.
No pasar esas indicaciones como generate_reply(instructions=...): el adaptador
Google las envía como rol model. No filtrar texto por palabras ni aplicar
include_thoughts=false como supuesto arreglo (falló la prueba web). 53 tests
Python y llamada LIRA → NEXO → ELIAN → NEXO aprobados localmente con preguntas
escritas y voz real. Worker local reconstruido; main/UAM sin actualizar.
Ver SUBTITULOS_TRANSFERENCIAS.md y final-call.json en la carpeta de validación.
Micrófono físico, aceptación artística del equipo y pruebas UAM siguen aparte.
