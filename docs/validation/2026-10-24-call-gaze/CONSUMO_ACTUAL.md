# Consumo observado de la demo web

24 octubre 2026 · código `1e53491` · Mac Apple M5, 24 GiB de memoria unificada.
Frontend de producción en localhost:3500. Prueba nueva con voz real de Gemini
Live y transferencias LIRA → NEXO → ELIAN. No se ejecutó Unreal para renderizar.

## RAM medida, no tamaño del archivo

| Avatar durante la llamada | RSS medio de la pestaña | Pico RSS observado | Muestras |
|---|---:|---:|---:|
| LIRA | 272,38 MiB | 314,31 MiB | 22 |
| NEXO | 268,20 MiB | 325,56 MiB | 30 |
| ELIAN | 263,05 MiB | 269,70 MiB | 14 |

RSS es memoria residente del proceso renderer de Chrome (PID 27599, identificado
con el Administrador de tareas y la pestaña activa). Incluye aplicación,
JavaScript, audio y recursos residentes de ese proceso; no es memoria exclusiva
del archivo GLB ni toda la GPU. Puede incluir páginas compartidas. No sumarlo
con el indicador «Espacio en memoria» de Chrome: son contabilidades distintas.

El Administrador de tareas también mostró ~192 MB para otra pestaña VIVA que ya
estaba abierta. Esa cifra puntual **no es el resultado de esta tabla**, ni una
medición de VRAM. El benchmark reutilizó una pestaña previamente calentada con
preview y alternó chat abierto/cerrado; no representa un arranque limpio ni un
ensayo estadístico comparable entre modelos. Las muestras abarcan habla y pausas.

## Servicios locales en Docker

Durante las fases de avatar, la suma de uso de memoria reportada por Docker fue
1.959–1.974 MiB de media (~1,91–1,93 GiB), con máximo conjunto de 2.173 MiB
(~2,12 GiB). Había otra llamada VIVA existente y otras pestañas abiertas; no se
interrumpieron. Esta cifra **no es costo marginal por usuario**.

Detalle de la fase NEXO, en MiB:

| Servicio | Media | Pico |
|---|---:|---:|
| Agente Python | 1.529,17 | 1.697,79 |
| Frontend Next.js | 119,72 | 127,70 |
| LiveKit | 88,68 | 101,10 |
| Qdrant | 79,36 | 122,40 |
| Knowledge sync | 74,60 | 74,60 |
| Colector de telemetría | 50,85 | 57,02 |
| PostgreSQL de telemetría | 31,63 | 32,75 |

Los picos de cada servicio no necesariamente ocurrieron simultáneamente. Docker
reporta memoria de contenedores, no todo el costo de su máquina virtual en macOS.
No sumar la VM de Docker otra vez a sus contenedores. Tras cerrar la llamada de
prueba, las últimas muestras del conjunto bajaron a ~1,55 GiB; no es evidencia
suficiente para certificar ausencia de fugas en sesiones largas.

## GPU y límites

En este Mac CPU/GPU utilizan memoria unificada. No se midió VRAM dedicada de
NVIDIA. El RSS del proceso GPU de Chrome es compartido con otras pestañas y
no representa toda su memoria gráfica. Tampoco es atribuible solo a VIVA.

El visor calcula ~37,3 MiB de texturas para LIRA, 25,3 para NEXO y 24,0 para
ELIAN. Son estimaciones de recursos, **no mediciones de VRAM total**: faltan
buffers del driver, framebuffer, navegador y compositor. No se suman a RSS
como si fueran memoria independiente.

Resultado práctico: la pestaña web medida estuvo por debajo de 326 MiB RSS;
no consume 10–12 GiB como una instancia del editor Unreal. No implica que se
puedan multiplicar esas cifras para garantizar un número de usuarios: el render
ocurre en cada cliente, mientras voz, herramientas y servicios tienen su propio
costo compartido y por sesión. UAM/RTX4050 y concurrencia necesitan su prueba.

## Evidencia y reproducción

- [Resumen numérico](current-memory.json).
- [90 muestras originales](memory-samples.jsonl), con hora UTC, fase, RSS y Docker.
- Intervalo aproximado de 5 s (3 s de espera más la consulta Docker).
- Fase `welcome`: incluye arranque/conexión, no usar como baseline inactivo.
- PID identificado en la UI de Chrome; `ps -axo pid,ppid,rss,command` proporciona
  RSS en KiB. Se almacenaron solo PID/clase/bytes, no argumentos ni datos de otras apps.
- `docker stats --no-stream`: uso instantáneo de los servicios `edutech-voice-local-*`.
- Solicitudes de prueba escritas, respuestas habladas del proveedor; sin archivo
  de audio guardado. No es prueba de interrupción acústica por micrófono.

## Hallazgo que impide declarar cerrada la presentación

En esta llamada, los subtítulos de dos transferencias incluyeron metainstrucciones
y un segmento rotulado «Reasoning». No se certifica si ese prefijo también fue
pronunciado: no se guardó audio. El código instalado del plugin 1.8.2 ya excluye
partes `thought` y usa `output_transcription` para salida de audio.

Cuatro pruebas directas del proveedor (entrada normal y contexto parecido a un
handoff, con configuración predeterminada y `include_thoughts=False`) devolvieron
audio y transcripción sin ese marcador. No reproducen toda la integración y no
prueban que esté corregido. No se cambió el modelo, las voces ni los prompts, ni
se añadió un filtro textual que pudiera cortar respuestas válidas.

Siguiente comprobación: reproducir con AgentSession y contexto completo de
transferencia, distinguir la fuente de los eventos de texto y validar cualquier
arreglo tanto en subtítulos como en voz. La demo no se declara perfecta por
aprobar tests del renderer.

Referencias oficiales para investigar ese hallazgo:
[LiveKit Gemini Live](https://docs.livekit.io/agents/models/realtime/gemini/) y
[capacidades Live API](https://ai.google.dev/gemini-api/docs/live-api/capabilities).
