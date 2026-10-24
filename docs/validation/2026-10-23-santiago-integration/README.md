# Integración de los GLB de Santiago y respuesta al audio

Fecha local: 23 octubre 2026. Continúa la integración `0225f0a` en
`chore/avatar-latency-audit`, PR #11; no despliega UAM ni modifica main.

## Modelos instalados

Se verificaron SHA-256, bytes, estructura GLB y manifiestos contra el repositorio.
La entrega `../avatars_santiago_glb` contiene **tres** modelos web, no seis:

| Personaje | Bytes GLB | Triángulos geométricos |
|---|---:|---:|
| LIRA | 4.666.084 | 75.781 |
| NEXO | 5.974.092 | 64.330 |
| ELIAN | 4.592.212 | 61.977 |

Hashes en [assets.json](assets.json). Todos coinciden con los manifiestos
canónicos existentes; se conservaron sus revisiones técnicas y sus límites de
aceptación artística. No se alteraron mallas, texturas, ropa, identidad ni rigs.
Los GLB y fondos permanecen fuera de Git. Los candidatos Mac anteriores se
conservan; sus manifiestos de vista previa se apartaron a
`data/local-avatar/candidates-before-santiago-20261023/` para que la vista previa
muestre ahora exactamente el modelo utilizado por las llamadas.

## Sincronización

Se mantiene un único audio de salida, reproducido por LiveKit. El analizador
lee PCM del track remoto, nunca del micrófono ni de una voz sintetizada aparte.
La animación emplea apertura, redondeo y extensión inferidos de energía y bandas;
**no reconoce fonemas**. Las caras originales no incluyen un conjunto de visemas
faciales etiquetados; el rig existente mueve huesos de mandíbula/labios.

Cambios:
- Ventana FFT: 1.024 muestras. La energía usa los últimos 10 ms de PCM para no
  prolongar vocales con audio anterior que aún ocupa la ventana.
- Ataque de 20 ms, relajación de 35 ms y cierre en silencio de 20 ms (constantes
  de suavizado, no garantías de latencia completa).
- Dinámica lineal para conservar sílabas suaves; suavizado independiente de
  redondeo/extensión (55 ms) y menor rotación adicional del labio inferior. La
  mandíbula conserva su recorrido; no se modifica el GLB ni la pose base.
- Verificación de reproducción efectiva: track activo, contexto ejecutándose
  y elemento de audio con reproducción habilitada. Al pausar, silenciar,
  desconectar o reemplazar el track se restablece el reposo.
- La voz continúa aunque el analizador o el modelo fallen. Se conserva el
  límite de 30 FPS, un avatar activo y liberación al transferir entre agentes.

Base técnica: [analizador LiveKit](https://docs.livekit.io/reference/client-sdk-js/functions/createAudioAnalyser.html)
y [PCM de AnalyserNode](https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode/getFloatTimeDomainData).
La comprobación de reproducción corresponde a la salida HTML de LiveKit usada
por esta app; activar su salida Web Audio experimental requeriría adaptar esa
comprobación. No se aplicó una compensación arbitraria para Bluetooth/altavoces.

## Telemetría de la llamada

Antes, el renderer emitía muestras en la ventana del navegador pero nadie las
persistía en la sesión. Ahora `AvatarStage` entrega datos al `MediaTelemetry`
de su propia sesión mediante contexto React; el preview sintético no participa.

Evento v2 `avatar_quality_sample`: primera ventana disponible y luego cada
10 s con renderizado activo. Incluye el personaje y hash exactos, FPS medio y
mínimo de las muestras, tiempo de envío de render, primera imagen, geometría,
texturas estimadas, heap JS, tamaño del lienzo, escala adaptativa y controles de boca disponibles.
Se enlaza con `app_session_id`, conversación, intento y sesión de medios por el
contexto firmado. No asigna un `turn_id` por proximidad horaria ni confunde el
personaje visual con la atribución de consumo del proveedor.

| Medición | Interpretación |
|---|---|
| `acoustic_onset_to_pose_max_ms` | Máximo desde actividad PCM detectada hasta pose visible calculada en las muestras. Puede ser 0 en el mismo frame. |
| `silence_to_rest_max_ms` | Máximo desde silencio PCM detectado hasta pose bajo umbral de reposo. |
| `onset_observations` / `close_observations` | Número de transiciones efectivamente observadas; sin observación, duración null. |
| `analysed_frames` / `speech_frames` | Cobertura de análisis; no duración de audio facturable. |
| `playback_status` | Estado en la última lectura: active, silent, blocked o unavailable. |
| `window_ms` / `sample_count` | Tiempo entre informes y número de muestras de rendimiento incluidas. Una pestaña oculta puede prolongar la ventana. |

Son observaciones acústicas locales, no desfase audiovisual medido a la salida
del altavoz, ni puntuación de sincronía de fonemas. El heap JS no es RAM total,
y las texturas estimadas no son VRAM total. Primera imagen corresponde a una
carga y puede repetirse: no sumar ni tratar cada evento como una nueva carga.

Panel: `/admin` → sesión → **Todos los eventos** → **Avatar y respuesta al audio**.
La cola no bloquea la voz; limita eventos y reintenta fallos. No se envían PCM,
espectros, audio grabado ni texto en estas muestras. El esquema estricto rechaza
campos adicionales. Desplegar colector actualizado antes del frontend nuevo.

## Verificaciones reproducibles

- Frontend: 47 pruebas aprobadas, 3 omitidas (manifiestos de candidatos Mac
  retirados de la vista previa); los tres GLB canónicos sí se prueban.
- TypeScript, lint y build aprobados.
- Telemetría: 27 pruebas aprobadas con PostgreSQL en una base desechable `test`,
  incluyendo persistencia y lectura del nuevo evento, identidad de sesión,
  autenticación, contrato exportado y prohibición de audio/texto arbitrario.
- [Respuesta sintética antes/después](synthetic-response.json): ráfaga de tono
  de 900 Hz, no voz. A 30 FPS, cierre de 150 a 83,3 ms; a 60 FPS, 150 a 100 ms;
  a 15 FPS, 116,7 ms en ambos. No extrapolar estos valores a fonemas o red.

## Arranque y prueba del equipo

Desde Edutech, con `.env.voice` local configurado y Docker activo:

```sh
python3 scripts/voice_demo.py doctor
python3 scripts/voice_demo.py up
```

Abrir `http://localhost:3500`, elegir Avatar e iniciar la llamada. LIRA recibe;
pedir hablar con NEXO y ELIAN para comprobar la selección anunciada por el agente.
No hace falta Unreal. `3511` era el visor técnico sin backend; usar `3500` para
la integración completa. Para instalar en otro equipo, entregar los archivos
privados verificados de `avatars_santiago_glb` además del código del PR.

Pruebas de aceptación: voz real, pausas entre sílabas/frases, interrupción,
regreso al reposo, transferencia LIRA → NEXO → ELIAN, cierre/reconexión y nueva
identidad de sesión. Confirmar que las métricas aparecen en la misma sesión.
El modo Voz debe continuar sin cargar modelos. UAM, dispositivos de salida y
concurrencia necesitan validación aparte.

## Rendimiento y latencias: cierre de esta iteración

El renderer pedía `low-power`. Ahora solicita `high-performance`: es una
preferencia al navegador, no garantiza que Windows elija la RTX. Véase
[WebGL powerPreference](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/getContext).
Se limita a 30 FPS y 1280×720. Tras calentamiento, tres ventanas consecutivas
por debajo de 24 FPS bajan la escala a 0,85, 0,70 y hasta 0,55, con cinco
ventanas de espera entre ajustes. La recuperación exige veinte ventanas a
29 FPS o más, con espera adicional para evitar cambios continuos de nitidez.
Esto reduce hasta aproximadamente 70 % de los píxeles; **no significa 70 %
menos de RAM/VRAM**, ni soluciona por sí solo un cuello de botella de CPU.
Modelos, texturas e iluminación se conservan. Una pestaña oculta suspende render.

Se corrigió además el reloj de conexión: la preparación anticipada del próximo
token no debe iniciar el cronómetro ni reasignar eventos de la llamada anterior.
El inicio ahora corresponde al clic en iniciar; las credenciales que caducan antes
de conectar pueden renovarse. Los registros históricos no se modificaron.

Dos llamadas posteriores a la reconstrucción se verificaron con voz de Gemini
Live, transferencia de personajes y cierre/reconexión. Evidencia numérica sin
texto ni audio: [live-call-performance.json](live-call-performance.json).

| Medición local | Resultado observado |
|---|---|
| Conexión de medios desde clic, dos llamadas | 246 y 230 ms |
| Evento HTML `playing` desde clic | 523 y 506 ms |
| LIRA, 1280×720 | 29,33 FPS medios de informes; mínimo 28,29 |
| NEXO, 1280×720 | 30,12 FPS medios; mínimo 29,80 |
| ELIAN, 1280×720 | 30,13 FPS medios; mínimo 29,75 |
| Máximo cierre acústico observado por personaje | LIRA 67 ms; NEXO 33,6 ms; ELIAN 67,1 ms |

En las cuatro llamadas exploratorias del día, el panel registró una operación
RAG de 5,55 s y seis consultas de memoria con mediana de 0,93 s. Son tiempos
de herramientas concretas, no del renderizador ni una garantía de respuesta
completa. No se redujeron fuentes ni se eliminaron búsquedas para maquillar latencia.

Las ventanas de medición permiten medias ligeramente superiores a la cadencia
objetivo de 30 FPS. Son pocos informes de un **Mac M5 con 24 GB**, no un ensayo
estadístico, concurrente o del portátil de Santiago. `playing` no acredita el
primer sonido no silencioso. El cierre mide la pose calculada respecto al PCM,
no alineación fonética. La prueba sintética se reproduce desde
`agent-starter-react` con `node ../docs/validation/2026-10-23-santiago-integration/compare-speech.cjs`.

Capturas de tamaño completo: [NEXO](nexo-live.png), [ELIAN](elian-live.png).
Una captura estática confirma encuadre, no calidad de sincronización labial.

### Prueba comparable para Santiago

1. Usar el código del PR #11 y los tres GLB privados con los hashes de assets.json.
   Reconstruir colector y frontend; no mezclar el colector antiguo con eventos nuevos.
2. Conectar el portátil a corriente, cerrar Unreal y otros renders, abrir una sola
   llamada en Chrome/Edge con aceleración gráfica disponible. Registrar navegador,
   GPU utilizada y si la sesión se observa por escritorio remoto.
3. Durante 60 segundos por personaje, ocultar la transcripción para medir el avatar
   grande, pedir una respuesta de voz, dejar pausas y hacer una interrupción.
4. En `/admin` revisar la sesión → Todos los eventos → Avatar y respuesta al audio:
   comparar FPS, resolución, `resolution_scale`, envío de render y cierres. No comparar
   el avatar compacto de 319×180 con el grande de 1280×720 como si fueran iguales.
5. Si baja FPS pero conexión/audio siguen ágiles, investigar GPU/CPU/render. Si FPS
   se mantiene y la voz tarda, revisar tiempos de respuesta del agente, herramientas,
   RAG y red. La reducción de resolución no acelera la inferencia del modelo.
6. Cerrar, esperar y reconectar: debe haber un nuevo intento y un inicio de conexión
   por llamada; no contar la espera en la pantalla de bienvenida como latencia.

Aceptación pendiente en RTX4050/UAM: mantener al menos 24 FPS sostenidos en vista
grande con escala registrada, voz continua y retorno al reposo tras pausas. Ese
valor es un objetivo de prueba, no una promesa para cualquier equipo. La animación
actual es acústica; mejorar consonantes concretas requiere visemas alineados al
mismo audio o un modelo audio-a-cara y su evaluación de coste/latencia.

Durante una respuesta se observó texto de planificación en inglés antes del
mensaje en español. Se deja como incidencia del agente/proveedor para revisar
con Jacobo; no se copió el texto privado ni se alteraron prompts en esta tarea.
