# Subtítulos durante transferencias

24 octubre 2026 · validación local, PR #11. Sin despliegue UAM.

## Problema y corrección

Al pasar de LIRA a NEXO o ELIAN aparecieron indicaciones internas antes del
saludo en los subtítulos. Se reprodujo con los agentes reales y RoomIO en una
sala independiente: el prefijo ya venía en `output_transcription` de Gemini.
No lo añadía el frontend. No se grabó audio, por lo que ese diagnóstico no
establece si todo el prefijo también fue pronunciado.

El adaptador Google de LiveKit 1.8.2 envía las `instructions` de
`generate_reply()` como un turno con rol `model`. Esas indicaciones de entrada
podían continuarse como diálogo del asistente. Ahora las mismas frases están
en las instrucciones del agente, bajo «Solo al iniciar tu participación»;
`on_enter` anuncia el personaje y solicita la respuesta sin sembrar un turno
de conversación con una instrucción operativa.

Se mantienen voces, modelos, dominios, herramientas, memoria, contexto de
transferencia, reintento ante silencio y cancelación ante cierre/interrupción.
No se filtran palabras ni se recortan subtítulos mediante expresiones regulares.

## Verificación

- Regresión escrita antes del arreglo: falló para los tres agentes. Verifica
  que la indicación esté en instrucciones y que `on_enter` no la envíe como
  diálogo. Las pruebas de ciclo de respuesta también rechazan ese parámetro.
- Ruff aprobado; **53 pruebas Python aprobadas**.
- Sala diagnóstica con Gemini Live real: LIRA → NEXO → ELIAN, con audio generado
  y subtítulos recibidos por RoomIO, sin prefijos detectados tras el arreglo.
- Llamada web local con preguntas reales escritas: NEXO respondió sobre
  sobreajuste sin pedir repetir la pregunta; ELIAN respondió sobre VivaUAM.
  Ambos subtítulos fueron legibles y sin las indicaciones internas anteriores.
  ELIAN → NEXO también respondió la pregunta sobre redes neuronales, sin prefijos.
  Sesión y medios cerraron correctamente: [final-call.json](final-call.json).
- Los avatares conservaron mirada frontal, animación por audio y cambios de
  personaje. El frontend y los GLB no cambian por esta corrección.

Metadatos de los probes, sin transcripciones ni audio:
[caption-probes.json](caption-probes.json). Los indicadores de texto de esos
probes son ayudas diagnósticas, no un clasificador general ni garantía de que
un modelo generativo nunca producirá texto inesperado.

Se descartó un ensayo con `include_thoughts=false`: pasó un probe pero falló
después en la web. **No forma parte de la solución publicada.** Los probes
directos de API sin la secuencia completa de transferencia tampoco bastaban.

## Repetir en otro equipo

1. Actualizar la rama/PR y reconstruir el worker de voz, además del frontend
   si aún no tiene los cambios de mirada. Un cambio en Python no se aplica a
   procesos de llamada que ya estén abiertos.
2. Abrir `http://localhost:3500`, seleccionar Avatar e iniciar una llamada nueva.
3. Preguntar a LIRA «¿Qué es el sobreajuste en aprendizaje automático?».
   NEXO debe aparecer y responder a esa pregunta.
4. Pedir «Pásame con Elian. ¿Dónde puedo ver los cursos virtuales de la UAM?».
   ELIAN debe aparecer y responder sin instrucciones internas en los subtítulos.
5. Preguntar qué es una red neuronal para comprobar la transferencia de regreso
   a NEXO. Revisar también silencio, cierre de boca y finalización de la llamada.

Comando local, después de finalizar las llamadas abiertas:

```sh
docker compose --project-name edutech-voice-local --env-file .env.voice \
  -f compose.voice.yml up -d --no-deps --build voice-agent
```

La prueba usa preguntas escritas y respuestas de voz reales. Micrófono físico,
barge-in acústico, RTX4050/UAM y concurrencia siguen requiriendo pruebas en esos
entornos. No atribuir a este cambio latencia cero ni sincronía fonética.

Referencias de protocolo: [Gemini Live: capacidades](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
y [adaptador Gemini de LiveKit](https://docs.livekit.io/agents/models/realtime/gemini/).
La decisión se apoya además en el código de la versión instalada y las
reproducciones locales, no en asumir que una opción aislada del proveedor basta.
