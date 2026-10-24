# Pulido sutil sobre la base aceptada — 23 octubre 2026

El usuario confirmó que la versión de Santiago se veía mejor y pidió conservar
ese estilo y pulirlo. El ajuste mantiene su rig, rangos, señales espectrales,
respuesta de mandíbula y cierre en silencio. Solo amplía la transición de
redondeo/extensión a una constante de 55 ms (antes 35/45 ms). No añade espera de
audio, modelos, servicios ni geometría. El cierre conserva 25 ms de constante.

`createSpeechMotion()` usa este pulido. La variante `santiago` conserva la
referencia exacta para comparar en el visor, donde «Movimiento de labios» permite
repetir el mismo archivo con ambos métodos. Cambiar método detiene la prueba;
no hay dos salidas de audio simultáneas. El JSON identifica qué variante se midió.
Las llamadas usan el pulido por defecto. Se conserva una salida LiveKit.

## Verificación

- 53 pruebas frontend aprobadas; 3 omisiones de candidatos privados ausentes.
- A 15/30/60 FPS, misma apertura de mandíbula en todos los frames; oscilación
  de formas reducida con espectro alternante; formas sostenidas iguales;
  vuelta a reposo en menos de 134 ms en la prueba de silencio sintético.
- `comparison.json`: frase sintética española de 9,27 s, PCM mono 48 kHz.
  Recorrido acumulado de redondeo/extensión reducido 7,94–8,46%; diferencia RMS
  de formas 0,035–0,041 en escala 0–1. Apertura idéntica, diferencia máxima 0.
  Este indicador cuantifica movimiento, no «calidad» ni precisión fonética.
- Comparación reproducible desde la raíz: `node
  docs/validation/2026-10-23-subtle-lip-polish/compare.cjs
  agent-starter-react/public/avatars/articulation-sample.wav` (en una línea).
  El archivo sintético queda fuera de Git. No usar grabaciones de conversaciones.
- Lint y TypeScript aprobados. Se conserva el diseño y los GLB de Santiago.

No es reconocimiento de fonemas ni se afirma sincronía perfecta. La selección
A/B permite comprobar el pulido sin perder la referencia que el usuario aceptó.
No se midió la RTX4050/UAM ni se desplegó allí. Las mediciones son locales.

Prueba del visor en Chrome local: LIRA con la frase completa, ~30 FPS, 10 pausas,
máximo silencio detectado → reposo de 101 ms. Se comprobó cambio entre «Referencia
de Santiago» y «Suavizado sutil»; cambiar método detiene y limpia las métricas de
la prueba anterior. El motor compartido se aplica a los tres modelos canónicos;
esta revisión del navegador fue con LIRA. No es una nueva llamada Gemini.
