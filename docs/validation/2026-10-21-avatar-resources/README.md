# Consumo local de los avatares web — 21 de octubre de 2026

LIRA de Juan y NEXO funcionaron con voz real del agente y renderizado en el navegador. Ambos mantuvieron aproximadamente 30 FPS a 960 × 540. Unreal estaba cerrado. Las cuatro pruebas terminaron sin errores de JavaScript ni fallos en los contadores.

Son mediciones observadas en este equipo, no un consumo fijo ni un máximo garantizado. Las tablas muestran **promedio / pico muestreado**, salvo indicación distinta. MiB = 1.048.576 bytes; GiB = 1.073.741.824 bytes.

## RAM y CPU

| Escenario | RAM privada residente del navegador (MiB) | Memoria privada comprometida (MiB) | Memoria reportada por Docker (MiB) | CPU navegador (%) | CPU servicios (%) |
|---|---:|---:|---:|---:|---:|
| Portada | 245.7 / 249.1 | 350.2 / 357.6 | 1350.8 / 1353.3 | 0.03 / 0.11 | 0.30 / 0.32 |
| Solo voz (LIRA) | 450.6 / 484.7 | 578.3 / 612.0 | 1697.8 / 1713.3 | 3.08 / 4.85 | 3.66 / 10.03 |
| LIRA + voz | 596.6 / 642.7 | 709.6 / 759.2 | 1708.2 / 1724.1 | 3.83 / 7.70 | 3.54 / 10.59 |
| NEXO + voz | 555.9 / 616.9 | 659.1 / 727.5 | 1729.8 / 1734.4 | 3.49 / 5.89 | 2.64 / 7.76 |

La RAM del navegador es la suma de WorkingSetPrivate de su árbol de procesos aislado. La memoria comprometida incluye páginas que pueden estar fuera de la RAM física; no se suma a la residente. La CPU se expresa sobre los 12 procesadores lógicos del equipo. Docker usa originalmente 100% por núcleo; aquí se normalizó dividiendo entre 12. Los contadores se consultan de forma cercana, no atómica.

Frente a solo voz, LIRA añadió **146.0 MiB** de RAM privada residente media al navegador. NEXO quedó **105.3 MiB** por encima de esa referencia. La comparación de NEXO también cambia de agente y respuesta, por lo que no aísla exclusivamente el costo de su malla.

## Memoria gráfica y rendimiento

Todas las pruebas usaron **AMD Radeon 740M integrada, Direct3D 11**, confirmado por Chrome y por la correspondencia LUID de los contadores Windows con DXGI. La RTX 4050 no registró asignaciones atribuibles a los procesos de este navegador. Su ocupación global por otras aplicaciones no se atribuye al avatar.

| Escenario | Segmento gráfico dedicado AMD (MiB) | Memoria gráfica compartida AMD (MiB) | Motor GPU más ocupado (%) | FPS medios |
|---|---:|---:|---:|---:|
| Portada | 18.7 / 18.7 | 42.7 / 43.5 | 0.0 / 0.0 | — |
| Solo voz (LIRA) | 30.8 / 32.5 | 163.5 / 184.5 | 1.5 / 5.0 | — |
| LIRA + voz | 19.8 / 30.8 | 234.6 / 254.1 | 5.9 / 6.0 | 30.00 |
| NEXO + voz | 24.4 / 40.6 | 176.4 / 204.7 | 4.8 / 5.0 | 30.00 |

En la GPU integrada, el segmento dedicado procede de memoria reservada por el sistema; no es VRAM de la NVIDIA. La memoria compartida usa RAM del sistema. Estos contadores describen asignaciones gráficas, no bloques adicionales que se deban sumar sin más a los contadores de RAM. El porcentaje GPU se obtiene sumando los procesos del navegador por motor físico y tomando el motor más ocupado; no se suman porcentajes de motores distintos. Los contadores GPU enteros tienen poca resolución para cargas pequeñas.

| Modelo | Archivo GLB | Triángulos de geometría / dibujados | Joints | Draw calls | Texturas estimadas | Geometría en buffers | Carga local registrada |
|---|---:|---:|---:|---:|---:|---:|---:|
| LIRA | 4.45 MiB | 75,781 / 76,031 | 486 | 15 | 37.33 MiB | 3.44 MiB | 564 ms |
| NEXO | 5.46 MiB | 59,578 / 59,578 | 235 | 7 | 24.00 MiB | 2.25 MiB | 374 ms |

El GLB es descarga/almacenamiento, no consumo de RAM. Texturas y buffers son estimaciones del contenido y no reemplazan los contadores reales de memoria gráfica. La carga local incluye obtención y preparación del modelo, no garantiza el tiempo de primer cuadro ni representa una descarga por Internet. Los FPS están limitados a 30 por diseño. Se excluyeron del cálculo de FPS los pocos eventos con el chat desplegado (visor reducido); las muestras de recursos abarcan toda la ventana, incluyendo esos cambios breves.

## Servicios locales

Memoria media que reporta Docker, MiB. Incluye únicamente el proyecto edutech-voice-local; los servicios históricos ajenos no se agregan a esta tabla.

| Servicio | Portada | Solo voz | LIRA + voz | NEXO + voz |
|---|---:|---:|---:|---:|
| voice-agent | 882.6 | 1214.5 | 1214.0 | 1227.5 |
| frontend | 104.5 | 106.7 | 107.3 | 107.7 |
| telemetry | 46.2 | 46.9 | 47.2 | 46.6 |
| knowledge-sync | 78.2 | 78.1 | 78.1 | 78.0 |
| telemetry-db | 42.9 | 43.3 | 43.5 | 43.7 |
| qdrant | 112.3 | 112.7 | 113.7 | 112.8 |
| livekit | 84.1 | 95.5 | 104.5 | 113.5 |

La máquina virtual WSL completa, con sus caches, sistema y otros contenedores, tuvo los siguientes valores residentes. **Docker ya está dentro de WSL: no sumar ambas filas como consumos independientes.** La memoria de WSL crece y se retiene entre pruebas; su diferencia no demuestra una fuga del avatar.

| Escenario | WSL residente total (MiB), promedio / pico | RAM libre global (GiB), promedio / mínimo |
|---|---:|---:|
| Portada | 1695.0 / 1698.8 | 1.15 / 1.04 |
| Solo voz (LIRA) | 2197.0 / 2230.5 | 0.60 / 0.35 |
| LIRA + voz | 2366.5 / 2411.5 | 0.66 / 0.45 |
| NEXO + voz | 2500.6 / 2520.5 | 0.66 / 0.29 |

El equipo dispone de 15,23 GiB de RAM utilizable (16 GB nominales). Durante la prueba la RAM disponible llegó a 0,29 GiB y Windows mantenía aproximadamente 44 GiB comprometidos entre todos los programas. No significa que el avatar ocupe 44 GiB: incluye todo el sistema y memoria respaldada por paginación. La captura background-processes.json documenta aplicaciones abiertas sin leer sus documentos ni cerrarlas. Esta presión de memoria limita la generalización del resultado a un equipo recién iniciado.

## Audio, red y alcance

| Escenario | Audio RTP recibido durante el tramo medido | Tasa media recibida |
|---|---:|---:|
| Solo voz (LIRA) | 368.8 KiB en 55.1 s | 54.9 kbit/s |
| LIRA + voz | 294.7 KiB en 55.1 s | 43.8 kbit/s |
| NEXO + voz | 544.8 KiB en 55.1 s | 81.0 kbit/s |

Son bytes de audio RTP recibidos por el navegador, no todo el tráfico de red: se excluyen señalización, cabeceras, llamadas del backend a proveedores y descargas iniciales del GLB. La entrada del micrófono fue silencio sintético, por lo que su tasa de subida no representa una conversación humana. Hubo audio con energía positiva, reproducción activa y estados speaking/listening. No se midieron consumo eléctrico total, batería, costos monetarios del proveedor ni recursos internos de Gemini en la nube.

## Método y reproducibilidad

- Inicio: 2026-10-21T22:42:42.442Z; fin: 2026-10-21T22:47:44.515Z (UTC).
- CPU: AMD Ryzen 7 7445HS w/ Radeon 740M Graphics     ; 12 procesadores lógicos. Chrome 155.0.8059.86.
- Chrome aislado en modo headless con aceleración gráfica; viewport 1280 × 900, DPR 1, visor 960 × 540. No es una medida de todo Codex ni del navegador personal.
- Portada: 30 segundos y 6 muestras. Cada llamada: 60 segundos y 12 muestras de recursos, aproximadamente una cada 5 segundos. Son picos muestreados después del calentamiento, no picos instantáneos de arranque.
- Un navegador nuevo por escenario, una sola llamada de prueba simultánea. NEXO se alcanzó por transferencia desde LIRA, como en la aplicación. Se verificó el atributo del agente y el canvas correcto.
- Dos intervenciones escritas durante cada ventana mantienen alternancia de voz y escucha. No es una prueba de estrés ni de concurrencia ni una prueba prolongada de fugas.
- Windows CIM para memoria/CPU/GPU; DXGI para identificar adaptadores; docker stats para servicios; eventos del visor para FPS/geometría; WebRTC getStats para audio. Docker expresa memoria en valores redondeados.
- La CPU del navegador usa deltas de tiempo de los procesos presentes en muestras consecutivas. Los procesos muy breves que nacen y mueren entre muestras pueden no quedar representados.
- No se cambió configuración, voces, modelos ni servicios de la aplicación. Los navegadores de prueba se cerraron al terminar. Unreal permaneció cerrado.

Evidencia: [resumen completo](summary.json), [muestras CSV](samples.csv), [datos originales](audit.json), [LIRA](avatar-lira.png), [NEXO](avatar-nexo.png). Scripts de medición conservados en data/local-avatar/resource-audit-20261021 del repositorio local.

La conclusión defendible es que el frontend con un avatar y voz mantuvo 30 FPS usando alrededor de 0,54–0,58 GiB de RAM privada residente, mientras los servicios locales reportaron 1,67–1,69 GiB. El presupuesto debe contemplar además WSL/Windows, recursos compartidos y las otras aplicaciones; sumar mecánicamente todos los contadores daría un total incorrecto.
