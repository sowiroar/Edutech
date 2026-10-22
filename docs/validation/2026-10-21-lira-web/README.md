# LIRA de Juan en el navegador — 21 octubre 2026

Procedencia verificada: `/Game/VIVA/Avatars/Lira/Maps/L_Lira`, `BP_Lira`, historial
JuanGonzalezx (`92869b3`). No es la candidata histórica de Santiago.
Modelo SHA-256 `87da34733fb1ffce0433daa6a7da9047e28b4e665abb70598f46897ae875a431`.
Exportación local: `D:/EdutechRuntime/web-export/20261021-214541-lira`.

## Conversión y revisión visual

- Cara, cuerpo y uniforme originales; materiales faciales reordenados antes del
  bake para evitar dientes sobre la piel. EyeShell transparente, iris originales.
- Cabello y cuello originales; sin Groom en tiempo real. Las cejas usan las
  tarjetas y el atlas SlightArch del personaje, ajustados a su superficie facial
  y unidos con los pesos de sus huesos. Se preserva su silueta en el plano frontal.
- Líneas del uniforme y trazos faciales traducidos de los materiales originales
  de Juan a shader web: glTF no reproduce su material de dos UV ni decal diferido.
- Reposo de 10 segundos, canales comunes copiados a ropa y cara, dos ciclos
  inspeccionados. Apertura de boca por amplitud y regreso al reposo revisados.
- No se guardaron mallas, materiales ni mapas de Unreal. Estado Git de los dos
  directorios LIRA comprobado limpio después de exportar; exportador cerrado.

Las capturas incluidas son evidencia de revisión técnica, no aprobación estética
del usuario. La iluminación WebGL difiere de Unreal; no es una copia píxel a píxel.
El control por amplitud no equivale a visemas ni a sincronización fonética.

## Recursos observados en vista previa

GLB: 4.45 MiB (4,666,084 bytes), 75,781 triángulos geométricos, 486 articulaciones,
3 skins y un clip. El contador de render muestra 76,031 triángulos por una pasada
adicional de transparencia, 15 llamadas de dibujo. Canvas 960 × 540 y límite 30 FPS.
21 muestras de desarrollo; tras el calentamiento se mantiene cerca de 30 FPS.
El primer fotograma compila shaders y no se presenta como rendimiento estable.
Texturas+mipmaps estimadas: 37.3 MiB; geometría: 3.44 MiB. No son RAM total ni VRAM.
No se ha medido el consumo aislado total de LIRA; no extrapolar la medida previa
de NEXO a este personaje. Sin errores JavaScript/WebGL en la revisión.

`lira-preview.json` guarda la muestra; las PNG muestran reposo, boca y repeticiones.
`manifest.json` conserva la revisión técnica y la procedencia. La aceptación
visual del usuario y el uso con micrófono humano se verifican aparte.

## Prueba de conversación

Frontend y agente locales reconstruidos; ambos puertos 3000/3500 devuelven
LIRA y NEXO, con LIRA en recepción. La primera prueba descubrió que `on_enter`
intentaba publicar antes de la conexión; se adelantó `ctx.connect()` a
`session.start()`. Voces, prompts, roles y transferencias permanecen iguales.

La repetición pasó en producción local: atributos iniciales `[LIRA]`, único
canvas LIRA y ningún render NEXO antes de transferir. Se envió por texto una
pregunta de prueba solicitando Nexus; luego se recibió `avatar.character=NEXO`,
estado `speaking`, canvas NEXO y un audio reproduciéndose. Audio entrante:
96,105 bytes, energía no nula; conexiones WebRTC establecidas. Cero errores JS.
Evidencia: `lira-to-nexo.json`, `lira-call-initial.png`, `lira-to-nexo.png`.
Se usó micrófono artificial silencioso, no se captó ni grabó voz humana.
Telemetría respondió 409 durante el inicio y luego 200; esta prueba no certifica
su totalidad. Dev 3501 y el exportador de Unreal quedaron cerrados.

Comprobaciones: TypeScript, formato de los materiales web, build Next/Docker,
15 pruebas del frontend, 9 Python del exportador/optimizador, 4 pruebas existentes
de voces/personajes y 1 regresión del anuncio inicial. La regresión ejercita el
arranque y el anuncio reales extraídos del módulo con transporte simulado, sin
iniciar RAG ni llamar proveedores. El flujo real se valida con la prueba anterior.
