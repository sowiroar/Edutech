# NEXO: transferencia de voz y recuperación del rostro nativo

Revisión local del 21 de octubre de 2026, America/Bogota. Sustituye la variante
de superficie subdividida que el usuario rechazó. No constituye aceptación artística.

## Fallo de conversación

El usuario indicó que pidió «háblame de la adquisición» y NEXO quedó sin hablar
al pasar a ELIAN. Los registros de esa sesión muestran una transferencia desde
el saludo, un reintento seis segundos después y `rt_session is not available`.
Tras desconectarse el usuario, otro reintento encontró la sesión cerrándose.
La consulta institucional que llegó a la herramienta no correspondía a la frase
indicada por el usuario; no se puede concluir, solo con ese dato, dónde se alteró.

Se corrige el ciclo del saludo: transferencia, interrupción del usuario y cierre
terminan su espera. Un agente anterior no reintenta sobre la sesión del siguiente.
El reintento único permanece para silencio real. NEXO pide aclaración si una
pregunta es ambigua antes de inferir un trámite institucional. Se conservan las
voces Aoede/Puck/Kore, roles, modelo, contexto y RAG.

Las pruebas de regresión se escribieron antes del arreglo: fallaban ante cambio
de agente, cierre e interrupción. Después pasan las nueve pruebas de ciclo de
respuesta y las 21 pruebas seleccionadas de agente/arranque en conjunto. Ruff
pasa sobre el código del agente y el nuevo archivo de pruebas.

La prueba local posterior a la corrección introdujo la frase por texto dentro
de una llamada con audio de respuesta y micrófono sintético silencioso. NEXO
respondió y siguió activo. Esto comprueba la conversación y el audio de salida,
pero no reproduce la transcripción del micrófono del usuario.

En la llamada final NEXO contestó: «¿Te refieres a adquisición de datos, de
conocimientos o a otro tipo de adquisición?». Se mantuvo NEXO. La siguiente
petición explícita de hablar con ELIAN transfirió correctamente y ELIAN habló.
Los cuatro turnos LIRA → NEXO → NEXO → ELIAN mostraron audio recibido, un solo
avatar y cierre de boca al terminar; cero errores JavaScript. El registro de
esa ventana no repitió los errores de sesión ni los reintentos de silencio.
Resumen sin conversaciones reales: [call-summary.json](call-summary.json).

## Modelo web

Se exporta el DNA de `CH_Nexo_MateoNative`, se reconstruye una malla transitoria
sin renderizado y se recupera su LOD3 real. La piel contiene 5.048 triángulos,
como la de LIRA; no se interpola la antigua malla de 1.104 triángulos para simular
detalle anatómico. Se conservan los materiales, cuerpo masculino, ropa y pelo.

El importador transitorio usa otra convención de ejes. El conversor valida
límites y orientación y traslada los pesos por nombre al esqueleto original
ensamblado. No instala el esqueleto transitorio ni guarda assets de autoría.
Se verificó igualdad de posiciones, normales, UV, pesos e índices del cuerpo,
ropa y pelo; las matrices de enlace del nuevo rostro coinciden con las del
ensamblado original. La reducción a cuatro influencias sigue siendo aproximada.

| Dato | Modelo anterior rechazado | Modelo nativo instalado |
| --- | ---: | ---: |
| Bytes GLB | 5.957.372 | 5.974.092 |
| Triángulos totales | 64.150 | 64.330 |
| Triángulos de piel facial | 4.416 interpolados | 5.048 nativos |
| Joints ponderados | 235 | 420 |
| Clips de reposo | 1 | 1 |

SHA-256 vigente de NEXO:
`576ffcf55c1803b6ba4e4291e6cb6124a0855d08ff0e10fe403d5e753500228d`.
LIRA y ELIAN conservan sus modelos y los tres usan el fondo UAM compartido.

Las pruebas del exportador pasan: 27 aprobadas y una omitida por plataforma.
Las siete pruebas de rig/presupuesto gráfico también pasan con el modelo nuevo.
Se revisaron imágenes de reposo, apertura, redondeo y extensión de boca, con
regreso al reposo y sin errores JavaScript. La web local fue reconstruida y
entrega el nuevo hash. El commandlet de exportación nativa finalizó sin guardar
paquetes; la nueva etapa se incluye en futuras exportaciones de NEXO.

Muestra del visor a 960×540: 29 FPS, siete llamadas de dibujo, unos 26,7 MiB de
texturas estimadas y 2,59 MiB de datos de geometría. Es una muestra, no un nuevo
benchmark de RAM/VRAM total. El GLB pesa 5,70 MiB; eso no es su consumo en memoria.
La boca sigue usando análisis acústico aproximado, no visemas fonéticos.

Evidencia privada: `data/local-avatar/nexo-repair-20261021/`. Las capturas, DNA,
GLB, transcripciones sintéticas y registros quedan excluidos de Git. La extracción
original está en `D:\EdutechRuntime\web-export\20261022-nexo-native-face-probe`.

## Entrega

Paquete privado: `data/local-avatar/publication-20261021/viva-web-avatars-20261021-nexo-repair.zip`.
11.998.689 bytes; doce entradas comprobadas con sus hashes. SHA-256:
`77fe7e50216c111f7cf01e00450fd5bf7ff62325ca1daa0ed749e6e4a6aaa5e0`.

La revisión artística permanece pendiente. No se afirma equivalencia exacta con
Unreal, validación de todas las frases habladas, ausencia absoluta de fallos ni
certificación de sesiones largas. No se hizo commit, push ni despliegue UAM.
