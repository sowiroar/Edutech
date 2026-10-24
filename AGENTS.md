# Edutech — instrucciones y estado vigente

Actualizado el 21 de octubre de 2026. Leer README.md y docs/mvp/README.md.
Este repositorio contiene agentes, frontend y telemetría. La autoría Unreal
vive en el repositorio hermano ../Avatar; el submódulo Avatar fija un SHA.

Auditoría en curso del 22 de octubre: ver
docs/validation/2026-10-22-avatar-audit/README.md. Se trabaja desde la integración
0225f0a en chore/avatar-latency-audit; main y UAM no se actualizan automáticamente.
El exportador admite Mac y `--no-install`. Los candidatos regenerados necesitan
su propia revisión: no heredar aprobaciones del paquete privado del 21.
Los límites explícitos de los clientes RAG evitan models.get al inicializar;
no modifican el modelo de voz ni añaden un tope corto a las respuestas.

23 octubre: LIRA ya tiene atlas original y GLB candidato completo (4,44 MiB),
instalado solo en manifest.preview.json; ver docs/validation/2026-10-23-lira-export.
La fuente principal es UE 5.8.2 y las cejas se recuperaron con UE 5.8.4.
Los tres candidatos requieren aceptación visual y voz real antes de promoverlos.
Al instalar archivos GLB nuevos, reiniciar el servidor Next de producción.

Entrega de Santiago recibida el 23: los tres GLB coinciden con los manifiestos
canónicos y ya están instalados localmente para llamadas. Los preview Mac se
preservan en data/local-avatar/candidates-before-santiago-20261023 (ignorados).
Ver docs/validation/2026-10-23-santiago-integration/README.md. El evento v2
avatar_quality_sample enlaza render y respuesta acústica a la sesión; no audio
ni sincronía fonética. Actualizar colector antes de frontend. Prueba completa
local en puerto 3500; 3511 era solo visor sin backend.
Cierre: 47 tests frontend + 27 colector; dos llamadas nuevas con voz real y
telemetría persistida. Preferencia GPU de rendimiento y resolución adaptativa
para FPS bajos; no equivalen a validación RTX4050/UAM. Cronómetro inicia al clic,
no durante prefetch. Evidencia y pasos comparables en el informe citado.

## Trabajo y conservación

- Base de desarrollo: main. Features/bugfix/chore vuelven por PR a main.
  backp-fase1 es compatibilidad; backup-fase-2 conserva el respaldo histórico.
- Definir EDUTECH_SKIP_DEPLOY=1 al operar Git. No ejecutar setup/deploy o UAM
  por sincronizar archivos. No usar reset/clean/force-push ni stash automático.
- Conservar cambios ajenos, datos, voces, prompts, roles y RAG/Mem0.
- No versionar .env, tokens, contraseñas, bases generadas, cachés o exportaciones.
- Leer instrucciones del componente antes de modificarlo. No confundir una
  compilación o test sintético con aceptación de conversación, arte o despliegue.

## Avatar web vigente

- Tres modelos web locales: LIRA de Juan, NEXO y ELIAN; no afirmar seis.
- LIRA procede de /Game/VIVA/Avatars/Lira/Maps/L_Lira y BP_Lira. No sustituir
  por /Game/UniversityVirtualAssistant/FamiliaVIVA/LIRA/NewMap_LIRA_Studio.
- LiraAgent/Aoede recibe; NexusAgent anuncia NEXO/Puck. ElianAgent/Kore mantiene
  su avatar original. ATLAS/NOVA/NOA aún no tienen clases de agente en este worker.
  El worker nexus no es el personaje inicial.
- ctx.connect() precede a session.start(); preservar el anuncio inicial.
- El cliente admite hasta 90 s para la llegada del agente cuando se prepara en
  frío; el intento completo se limita a 95 s. Una desconexión debe abortar la
  espera de start() y liberar el botón. Ver lib/session-start.ts en el frontend
  y docs/validation/2026-10-21-lira-startup; no ocultar errores de red como arte.
- El frontend sigue avatar.character. Sin señal no elige NEXO por defecto.
  Un único modelo activo; liberar recursos al transferir y conservar voz ante fallo.
- Ropa y rostro usan canales comunes del cuerpo. No reintroducir el retarget
  por offsets de referencia que produjo intersecciones. Ver AVATAR_WEB.md.
- Boca por RMS y bandas espectrales (apertura/redondeo/extensión), sin reconocer
  fonemas. No afirmar sincronía fonética. Reexportar reinicia la revisión a
  pending; no aprobar automáticamente nuevas variantes ni cambiar assets originales.
- ELIAN usa /Game/VIVA/Avatars/Elian/Maps/L_Elian. Su exportación incluye materiales
  de ojos/dientes horneados sobre su propia malla; no usar la esfera de previsualización.
  LIRA, NEXO y ELIAN comparten Uam-virtual por petición del usuario.
- NEXO web usa ahora la geometría LOD3 del DNA original de CH_Nexo_MateoNative
  (5.048 triángulos de piel), con los huesos/bind matrices del ensamblado original.
  Se conservan torso, ropa, pelo y mapas. La subdivisión anterior fue rechazada
  visualmente por el usuario; no describirla como aprobada. Ver
  docs/validation/2026-10-21-nexo-repair/README.md para evidencia y límites.
- El reintento de saludo termina ante transferencia, cierre o interrupción;
  no confundirlos con silencio. Las preguntas ambiguas de NEXO se aclaran antes
  de enviar a ELIAN. No cambiar sus voces ni ampliar los dominios por este arreglo.
  LIRA reconoce Nexo/Nexus como el mismo especialista y transfiere también ante
  la petición explícita de hablar con él, aunque aún no haya una pregunta técnica.
- La síntesis documental conserva Gemini 2.5 Flash, temperatura 0,2, prompts y
  fuentes. rag_config.py limita solo el razonamiento interno a 512 tokens; no
  limita la longitud de respuesta. La inicialización RAG de NEXO se ejecuta fuera
  del bucle de audio. No aplicar esa configuración al modelo de voz Gemini Live.
- NEXO tiene piel mate en el visor: reducir reflejos no requiere reexportar ni
  cambiar texturas, cuerpo o rig. Los ojos conservan su material independiente.
- Modelos y fondos fuera de Git. Manifiestos y código sí se versionan.
  Seguir public/avatars/README.md dentro del frontend y THIRD_PARTY_AVATARS.md.
- No iniciar avatar_local.py, renderer nativo, --avatar o MJPEG para el visor web.
  La app no necesita Unreal en ejecución. Conservar los antecedentes nativos.

## Operación y evidencia

compose.voice.yml es el perfil local. Frontend 3000 y 3500, vista avatar-preview,
panel /admin. El frontend histórico no debe ocupar 3000. down conserva volúmenes.
Para reconstruir solo la web: python scripts/voice_demo.py web.
Scripts de exportación: avatar_web.py; configuración y resultados en
data/local-avatar (ignorado). El equipo actual conserva caché en D:/EdutechRuntime.

Evidencia vigente en docs/validation/2026-10-21-lira-web y
2026-10-21-avatar-resources. LIRA y NEXO: ~30 FPS a 960x540; RAM privada residente
media/pico navegador 596,6/642,7 MiB y 555,9/616,9 MiB. Docker medio 1708,2/1729,8
MiB. Pruebas de 60 s con entrada sintética y Unreal cerrado, no estrés ni fugas.
GPU AMD 740M integrada; no atribuirles VRAM global NVIDIA. No sumar memoria
compartida otra vez, Docker a WSL, ni compromiso privado a RAM residente.
La verificación posterior 2026-10-21-avatar-speech-style comprueba las formas
de labios y LIRA → NEXO → ELIAN en llamada. No reemplaza el benchmark de memoria.

## Telemetría y límites

Conservar contratos, TTL y captura opt-in de transcripciones; no guardar audio.
Desconocido se expresa null, no cero. No inventar costos completos o identidades.
Pruebas PostgreSQL solo en base test; no borrar datos reales. Moodle/SSO,
despliegue UAM, aceptación artística y concurrencia siguen sin certificación nueva.

Entrega y verificaciones: docs/mvp/ENTREGA_WEB_2026-10-21.md.
Las notas anteriores se conservan en docs/history/AGENTS-through-20261021.md;
son antecedentes, no instrucciones vigentes de arranque o ramas.

## Preferencia visual vigente: movimiento de Santiago

23 octubre, después de las pruebas de articulación: el usuario prefirió la
animación anterior. Rig y algoritmo acústico restaurados desde 0225f0a; FFT2048.
Se mantienen rendimiento adaptativo y telemetría. El clasificador experimental
no está activo. Ver docs/validation/2026-10-23-santiago-motion-restore/README.md.
No reutilizar mediciones previas de cierre como si fueran de esta restauración.

## Pulido solicitado sobre el estilo conservado

23 octubre: el usuario confirmó «Sí, conservar este estilo y pulirlo».
Se mantiene la base Santiago y se suavizan únicamente redondeo/extensión a 55 ms;
mandíbula, rangos y cierre iguales. El visor compara `smooth` con `santiago`.
Ver docs/validation/2026-10-23-subtle-lip-polish/README.md. No reintroducir el
clasificador experimental ni sustituir la identidad de los modelos.
