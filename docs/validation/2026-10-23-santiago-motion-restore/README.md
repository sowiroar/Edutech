# Recuperar la animación de Santiago — 23 octubre 2026

El usuario prefirió el movimiento anterior. La referencia comprobada es
`0225f0a` (autor Santiago, «integracion v1»), no una reconstrucción aproximada.

## Cambio

- Se recuperan exactamente el rig facial y el algoritmo acústico de esa base:
  mandíbula y control independiente del labio inferior con igual rotación,
  redondeo/extensión originales, RMS sobre la ventana completa, sensibilidad
  original y suavizado de entrada/salida de 35/45 ms.
- El analizador vuelve a 2048 muestras. No se añade ningún búfer de reproducción:
  LiveKit sigue siendo la única salida de audio.
- Permanecen resolución adaptativa, preferencia GPU de alto rendimiento,
  telemetría de render/carga y cierre cuando el audio no es audible.
  El RMS de 10 ms queda exclusivamente para medición, no para mover la boca.
- El experimento de clasificación de visemas, sus deformaciones adicionales y
  su banco de pruebas se conservaron fuera del código activo, bajo
  `data/local-avatar/articulation-experiment-before-santiago-restore/` (ignorado).
  No se incorpora el clasificador ni su modelo inglés a las llamadas.
- Sin cambios a GLB, voz, prompts, RAG, backend o UAM.

## Evidencia y límites

`comparison.json`: 1260 frames deterministas, 24/48 kHz y 15/30/60 FPS;
la diferencia máxima con la salida original de Santiago es 0. El rig coincide
byte por byte con su base. Es equivalencia de código/poses, no una evaluación
perceptual ni reconocimiento de fonemas.

Frontend: 47 pruebas aprobadas y 3 omitidas por candidatos privados ausentes;
las pruebas con los tres GLB canónicos instalados sí se ejecutan. Lint y
TypeScript aprobados. Compilación Docker y reconstrucción local completadas.
El visor sirve el cambio desde el puerto 3500. No se abrió otra llamada con
micrófono en esta validación; queda pendiente la comparación perceptual del usuario.

Para probar: recargar http://localhost:3500, iniciar modo avatar y hablar con
normalidad. Comparar frases suaves, vocales y pausas; interrumpir y comprobar
que vuelve a reposo. La vista `/avatar-preview?character=ELIAN` permite revisar
formas sin micrófono, pero su botón de movimiento es sintético y no valida audio.

No afirmar que los 33–67 ms documentados en el informe anterior se conservan:
esa medición pertenece al algoritmo anterior. Los eventos nuevos permiten
volver a medir con esta base. No hay una medición nueva de la RTX4050 de Santiago.
