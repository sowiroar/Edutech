# NEXO web — revisión técnica del 21 de octubre de 2026

Modelo SHA-256: `98e8754c1b6c5af760dce59f06bbf88c2750a6c8dfe6fa893b51a2bfcb96639a`.
La aceptación estética del usuario sigue pendiente. Esta revisión comprueba
ropa/cuello y ejecución técnica, no equivalencia exacta con la ilustración de
Familia VIVA ni sincronización fonética.

## Correcciones comprobadas

- Exportación fuente de Unreal 5.8 completada; corregido el setter de LOD que
  causaba `TypeError: 'bool' object is not callable`.
- Slots de la cara corregidos; la piel ya no usa el material de dientes.
- Pose del cuerpo transferida directamente a huesos comunes de cara y ropa;
  conservar offsets distintos de la cara producía intersecciones en el pecho.
- Mismos 59,578 triángulos; vértices idénticos compactados de 178,734 a 37,203.
  Sin guardar mallas ni mapas originales de Unreal.
- Texturas acotadas (normal de pelo 2048 → 1024), preferencia GPU low-power,
  máximo 30 FPS y 1280 × 720; sin Groom, sombras dinámicas ni simulación de tela.

## Medición de vista previa de producción

Chrome sin ventana de usuario, viewport 1280 × 900, canvas 960 × 540.
38 muestras después del calentamiento, unos 38 segundos; Unreal cerrado.
Baseline: portada de la misma aplicación, sin llamada. No extrapolar a móviles,
otros equipos, seis avatares simultáneos ni conversación real.

| Medida | Resultado |
|---|---:|
| Archivo GLB | 5,721,776 bytes (5.46 MiB) |
| Triángulos / llamadas de dibujo | 59,578 / 7 |
| FPS medio / mínimo | 30.00 / 29.79 |
| Envío del render en CPU, medio | 0.43 ms (no tiempo de GPU) |
| Texturas RGBA+mipmaps, estimación | 24.0 MiB |
| Datos geométricos, estimación | 2.25 MiB |
| Memoria privada Chrome, portada | 317.6 MiB |
| Memoria privada Chrome, avatar en reposo | 494.3 MiB |
| Diferencia respecto a portada | +176.7 MiB |
| Memoria privada durante prueba de boca | 497.6 MiB |
| Heap JavaScript máximo observado | 37.0 MiB |
| CPU Chrome normalizada a 12 procesadores lógicos | 1.60% |
| GPU usada por WebGL | AMD Radeon 740M, ANGLE/D3D11 |

La memoria privada suma browser, renderer y proceso GPU del Chrome de prueba.
No incluye Docker, todo Windows ni otros Chrome. La NVIDIA global pasó de
502 a 507 MiB: incluye otras aplicaciones y no representa VRAM de NEXO.
El visor usó GPU integrada; no es render solo por CPU.

Sin errores JavaScript ni solicitudes externas en preview. Reposo repetido,
apertura sintética de boca y retorno al reposo inspeccionados. También se
inspeccionaron poses en 0, 22.65, 45.2, 45.4 y 90.8 segundos: el clip dura 45.3 s
y mantuvo cuello/ropa antes y después de repetirse. El canvas desapareció al
volver a portada. Cambiar de pestaña en Chrome headless no cambió visibilityState;
la pausa/reanudación sí pasó con eventos de visibilidad simulados. Esto último
comprueba el controlador, no el comportamiento real de las pestañas de Windows.

## Archivos y reproducción

- `metrics.json`: resumen de la muestra, sin audio ni credenciales.
- `preview.png`, `mouth.png`: capturas revisadas de producción.
- Registro completo local: `data/local-avatar/web-qa-20261021/benchmark.json`.
- GLB bruto y procesamiento: `D:/EdutechRuntime/web-export/20261021-194503/`.
- Modelo instalado: `agent-starter-react/public/avatars/nexo/manifest.json`.

Revisión técnica del manifiesto: visual_review=passed, motion_review=passed,
mouth_mapping=amplitude-verified. Cada nueva instalación reinicia los campos.
No son aprobación estética del usuario. Para ver el modelo no se necesita
Unreal ni MCP: abrir /avatar-preview. Para conversar se requieren además los
servicios de voz y credenciales válidas. Pasaron compilación de producción local,
TypeScript, 10 pruebas de frontend y 8 pruebas Python de exportador/optimizador.

## Integración de voz

Frontend Docker reconstruido y disponible en http://localhost:3500. Servicios
locales existentes iniciados sin reconstruir/modificar agentes, roles ni prompts.
Prueba desde Chrome con dispositivo artificial silencioso (sin micrófono humano):
se eligió Avatar, inició la llamada y envió por chat una pregunta de prueba para
pasar de Lira a Nexus. Token HTTP 200, WebRTC conectado, un audio reproduciéndose,
atributo del agente `avatar.character=NEXO` y estado `speaking`, canvas NEXO visible.
Audio entrante: 96,210 bytes y energía no nula en la última prueba completa;
sin errores JavaScript. Captura en `integrated-call.png`.

Esto valida señalización, personaje, render y audio de respuesta del agente.
La boca usa amplitud, no visemas; no se afirma sincronía fonética ni conversación
humana validada. No se grabó audio. La telemetría devolvió un 409 inicial y después
200; no se declara una auditoría integral de telemetría terminada por esta prueba.

Para probar: abrir http://localhost:3500, elegir Avatar e iniciar llamada.
Lira inicia el flujo existente; pedir hablar con Nexus para ver NEXO asociado a
su agente. Para solo verlo, usar http://localhost:3500/avatar-preview.
La copia auxiliar del host en 3501 se detuvo al finalizar la migración a Docker.

### Recursos con llamada conectada

Segunda prueba con medición durante 30 segundos después de recibir la respuesta
de Nexus; incluye reposo posterior, no habla continua. Chrome usó la misma AMD
integrada. Memoria privada del navegador de prueba: 686.6 MiB al inicio y 605.8
MiB al final; CPU media del navegador 2.71% normalizada al equipo de 12 hilos.
Los contenedores sumaban aproximadamente 1.76 GiB en la muestra final, incluyendo
agente de voz (~1.279 GiB), frontend, LiveKit, RAG y telemetría. Es una muestra,
no un máximo; tampoco incluye el sobrecoste completo de Docker/WSL ni Windows.
Estas medidas son separadas del incremento de +177 MiB de la vista previa.
Detalle en `call.json`; no se grabó micrófono ni audio.

## Corrección del acceso por puerto 3000

La captura de la plantilla antigua correspondía a `edutech-frontend-1` en 3000.
Se detuvo únicamente ese contenedor y se conservó. El frontend vigente ahora
publica 3000 y 3500 en loopback. Se autorizó explícitamente el origen local 3000
sin desactivar la comprobación de origen: solicitudes desde un origen ajeno
siguen devolviendo 403. Ambas direcciones entregan la interfaz con selector
Avatar y crean sesiones con NEXO (HTTP 200); evidencia en `ports.json`.

Repetida la llamada desde 3000 con micrófono artificial silencioso y una pregunta
por texto: WebRTC conectado, NEXO visible, agente en estado speaking, un audio
reproduciéndose, 82,254 bytes recibidos y energía no nula, sin errores JavaScript.
Ver `call-3000.json` y `integrated-call-3000.png`. Unreal no estaba abierto.
Pasaron TypeScript, 13 pruebas seleccionadas y la compilación Docker.
Esta repetición comprueba acceso e integración; no es una nueva medición de RAM
ni una validación de micrófono humano o sincronía fonética. Solo NEXO tiene
exportación web disponible; no se presentan seis avatares como terminados.
