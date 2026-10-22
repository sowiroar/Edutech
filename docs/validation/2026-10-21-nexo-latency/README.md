# NEXO: espera de respuesta y acabado mate

Revisión local del 21 de octubre de 2026 (America/Bogota). Se atiende la demora
en preguntas después de transferir de agente y el exceso de brillo en la piel.

## Diagnóstico y cambio

En la sesión previa a este ajuste, transferir a NEXO tomó unos 0,3 segundos;
la consulta documental posterior tomó 8,59 segundos. Transferir a ELIAN tomó
unos 0,2 segundos y su consulta documental 14,07 segundos. La demora principal
observada estaba en la generación documental, no en la carga del avatar.

La síntesis conserva Gemini 2.5 Flash, temperatura 0,2, los prompts, documentos,
recuperación y fuentes. Se limita el razonamiento interno a 512 tokens, sin
imponer un máximo de longitud a la respuesta. Esta configuración se comparte
entre las consultas documentales de NEXO y ELIAN, no con Gemini Live. La
inicialización en frío del índice de NEXO pasa a un hilo para no bloquear audio.

La primera prueba completa reprodujo además una petición de hablar con «Nexo»
que LIRA respondió sin transferir. Sus instrucciones identificaban al especialista
como Nexus y definían el disparador por tema técnico. Se explicita en instrucciones
y descripción de herramienta que ambos nombres corresponden al mismo especialista
y que una petición directa basta, sin exigir una pregunta técnica adicional.
Este fallo de la prueba se conserva en la evidencia; no se cuenta como llamada aprobada.

Prueba aislada sobre la misma pregunta de créditos y materias de la
Especialización en IA: 11,46 segundos con la configuración anterior y 3,51
segundos con el presupuesto elegido de 512. Se conservaron los 25 créditos,
las materias enumeradas y las tres fuentes recuperadas. Una prueba exploratoria
con 256 omitió la electiva institucional; se descartó ese presupuesto.
Son muestras individuales dependientes de Google y de la red, no un percentil
de producción ni una evaluación completa de exactitud de respuestas.

## Apariencia

La piel facial y corporal de NEXO usa rugosidad completa, metalicidad cero y
reflejo especular atenuado en el visor. Se suaviza el mapa de normales facial y
la luz principal. Los ojos conservan su material independiente. No se cambian
texturas, geometría, cuerpo, pelo, rig, GLB ni assets de Unreal.

Se inspeccionaron reposo, apertura, redondeo y extensión de labios. La vista de
desarrollo a 960×540 mantuvo unos 30 FPS, siete llamadas de dibujo y 64.330
triángulos, sin errores JavaScript. No constituye un nuevo benchmark de RAM/VRAM
ni aprobación artística del usuario.

## Verificación

Las dos pruebas de regresión se escribieron y fallaron antes del cambio: faltaba
la configuración de generación y la inicialización bloqueaba el bucle de audio.
Después pasaron las 23 pruebas seleccionadas de consultas, ciclo de respuesta,
arranque, tareas en segundo plano y conocimiento. Ruff, ESLint, TypeScript,
Prettier y la compilación de producción finalizaron correctamente.

La segunda llamada completó los cinco turnos después de corregir el alias.
Se enviaron preguntas por texto dentro de una llamada con entrada sintética
silenciosa; el audio recibido se redujo a RMS, sin grabarlo. El tiempo hasta el
primer audio se mide desde Enter, con umbral RMS 0,02. No incluye reconocimiento
de voz ni detección del final del habla de un micrófono humano.

| Turno | Hasta primer audio recibido | Consulta documental |
| --- | ---: | ---: |
| LIRA → NEXO, petición por nombre | 2,34 s | No necesaria |
| NEXO, créditos y primer semestre | 5,15 s | 3,75 s |
| NEXO, siguiente pregunta sobre una asignatura | 5,49 s | 3,77 s |
| NEXO → ELIAN, oferta de pregrados | 9,27 s | 6,24 s |
| ELIAN, siguiente pregunta de inscripción | 4,19 s | 2,78 s |

Los cinco turnos tuvieron audio, movimiento de labios, regreso al reposo y un
único avatar correspondiente al agente activo. No hubo errores JavaScript ni
eventos de error en la telemetría de esa sala. La petición por nombre pasó de
no transferir en la prueba previa a transferir correctamente. La consulta amplia
de ELIAN sigue tardando más; no se presenta este cambio como respuesta instantánea
ni como eliminación de toda latencia. Resumen: [call-summary.json](call-summary.json).

La vista de producción también se verificó con el fondo UAM, apertura/redondeo/
extensión de boca, retorno al reposo y cero errores JavaScript. Una muestra final
dio 27 FPS mientras corría la prueba de llamada; no sustituye las mediciones de
recursos anteriores ni permite atribuir consumo exacto de memoria al material.

El agente y el frontend locales se reconstruyeron. La evidencia privada está
en `data/local-avatar/nexo-latency-20261021/`; no incluye grabación de audio.
Las preguntas de prueba son ficticias y su envío con fragmentos documentales a
Gemini fue autorizado por el usuario. No se hizo commit, push ni despliegue UAM.
