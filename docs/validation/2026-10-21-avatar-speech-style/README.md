# Avatares originales, materiales y boca — 21 octubre 2026

Prueba local con el frontend de producción en Docker, LiveKit y las respuestas
reales de Gemini. Entrada de micrófono sintética y silenciosa; preguntas escritas.
No se captó voz del usuario ni se guardó audio. Unreal permaneció cerrado.
La llamada ocurrió al final del 21 de octubre en America/Bogota (22 en UTC).

## Cambios

- NEXO mantiene su GLB anterior: cara, cuerpo, pelo, ropa, rig y reposo. El visor
  recupera el material azul y los circuitos/emblema usando los Custom originales
  de NativeFinal, corrige el brillo metálico del pelo y acerca la cámara.
- LIRA mantiene la versión de Juan y comparte la imagen Uam-virtual con NEXO.
- ELIAN se exporta de L_Elian con sus gafas, cabello gris, uniforme, mangas,
  cuello y estudio. Se reparan los slots de cara/ojos/dientes del exportador;
  cada textura se hornea sobre su propia malla y se verifican topología y UV.
  Una máscara de piel cubierta evita cruces de hombro bajo el uniforme web.
- El movimiento de boca usa el PCM recibido: RMS, bandas espectrales, puerta de
  silencio y transiciones suaves. Genera apertura, redondeo y extensión; la
  mandíbula y los labios se mueven en los ejes del rig importado. No reconoce
  fonemas ni produce visemas sincronizados por marcas de tiempo.
- Solo se ofrecen los tres agentes existentes: Lira/Aoede, Nexus/Puck,
  Elian/Kore. ATLAS/NOVA/NOA no tienen clases de agente en este worker.

## Llamada comprobada

| Recorrido | Audio recibido y labios activos | Reposo en pausas | Avatar correspondiente | Canvas activos |
|---|---|---|---|---:|
| LIRA | Sí | Sí | LIRA | 1 |
| Transferencia a Nexus | Sí | Sí | NEXO | 1 |
| Transferencia a Elian | Sí | Sí | ELIAN | 1 |

Cero errores JavaScript. La instrumentación confirmó RMS de voz y variación de
las tres formas de boca; el último valor fue cero en todos sus controles.
Las capturas durante voz y reposo se revisaron visualmente. El cierre en 133 ms
se comprobó en el test sintético, no se presenta como latencia medida de la llamada.
Los datos resumidos están en [call-summary.json](call-summary.json).

LIRA/NEXO/ELIAN duraron aproximadamente 25/48/18 s en sus ventanas de observación.
No es una prueba fonética, de lectura labial, de concurrencia ni de larga duración.
El viewport de navegador fue 1280×900; el avatar se dibujó a 960×540, con
miniatura temporal durante el envío de preguntas. La mediana fue ~30 FPS;
las medias incluyendo carga/transiciones fueron 28,76 / 29,77 / 28,81 FPS.
No se ocultan los mínimos de carga; están en el JSON.

Los datos de texturas/geometría del visor son estimaciones de sus buffers,
**no una medición de VRAM total ni de RAM residente**. El benchmark anterior
de RAM/GPU sigue identificado por su fecha y configuración; no se extrapola
a ELIAN ni a todas las sesiones.

## Conservación y entrega

No se guardaron cambios en assets de Unreal ni se modificaron voces, prompts,
roles, RAG o Mem0. glTF/WebGL conserva el diseño, pero su iluminación y shaders
no producen una imagen idéntica píxel a píxel a Unreal. Revisión técnica no
equivale a aprobación artística del usuario.

ELIAN: 4.592.212 bytes, 61.977 triángulos, 215 joints, un clip. SHA-256:
`d833245bb6380240dc4de22f4c317449e367a48b891a5cfe3f7ff8fa4f20f40d`.
NEXO y LIRA conservan sus hashes de la entrega previa.

Paquete privado de tres avatares en
`data/local-avatar/publication-20261021/viva-web-avatars-20261021-three-agents.zip`.
Incluye los modelos referenciados por los manifiestos, fondos, atribución e
instrucciones; verificadas integridad ZIP y sumas individuales. Su SHA-256 es
`8a328f4f14eee52f18fefa440150ac20f088a8790e03eb6cf6870ddea15ca9f2`.
Requiere el código actualizado del visor; los GLB por sí solos no cambian los shaders.

Resultados brutos y capturas: `data/local-avatar/speech-style-20261021/`, fuera
de Git. Exportación final: `D:/EdutechRuntime/web-export/20261022-000701-elian/`.
La exportación no se repite para iniciar el navegador.

## Comprobaciones

- 31 tests del frontend aprobados, incluidos controles faciales de los tres GLB.
- 22 tests Python de scripts aprobados; uno omitido por requerir runner Linux.
- TypeScript y ESLint aprobados; compilación de producción completada.
- Reconstrucción limitada al frontend local. No commit, push ni despliegue UAM.
