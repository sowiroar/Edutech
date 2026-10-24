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
