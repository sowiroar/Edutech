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

## Prueba repetible con voz sintética local

Se añadió «Probar con audio» solo al visor. Acepta un archivo local o, cuando
está instalado, el ejemplo sintético `public/avatars/articulation-sample.wav`.
No usa micrófono, red de voz, telemetría remota, clasificador ni modelos nuevos.
No guarda ni sube el archivo. El JSON de medición incluye el resultado acústico
con alcance explícito `local-file-preview-not-live-call`, sin nombre ni audio.
Una única salida Web Audio reproduce el ejemplo. Detener, terminar, cambiar
archivo o salir libera el contexto y vuelve a reposo. La prueba de posiciones
fijas y la prueba de audio se excluyen para evitar dos controladores simultáneos.

Frase sintética Paulina (macOS), 48 kHz, 9,27 s: «Mi mamá me mima. Papá prepara
pan. Fabiola firma flores. Uno, dos, tres. A, e, i, o, u.» La muestra es local e
ignorada por Git; cada colaborador puede usar una frase propia sin datos personales.

Resultados del navegador Chrome local en modo desarrollo, alrededor de 30 FPS:

| Avatar | Pausas observadas | Máximo silencio detectado → reposo |
| --- | ---: | ---: |
| ELIAN | 10 | 134 ms |
| LIRA | 10 | 101 ms |
| NEXO | 10 | 134 ms |

Son muestras de una ejecución y están cuantizadas por los frames. No permiten
comparar la rapidez de los personajes ni prueban precisión fonética, sincronía
con altavoces, llamadas Gemini o RTX4050. Se verificó también detener y repetir.
La preferencia perceptual del usuario sigue pendiente. No se cambia el algoritmo
ni el rig de Santiago para añadir este banco de prueba.

Frontend: 50 tests aprobados, 3 omisiones de candidatos ausentes. Los nuevos tests
cubren fin de reproducción, cancelación durante inicio asíncrono y errores,
exigiendo liberación de recursos y pose en reposo. Lint/TypeScript aprobados.
