# Prueba local de NEXO y consumo — 18 octubre 2026

> **Flujo suspendido.** Santiago aclaró que el avatar debe ejecutarse en el frontend,
> sin un renderer Unreal activo. No ejecutar el comando de preparación de este documento.
> Se conserva como antecedente técnico; el objetivo vigente es exportar un modelo web
> ligero y medir su ejecución en el navegador. El valor de 1,469 GiB de voz sigue vigente
> como muestra reportada, sin avatar.

## Estado comprobado

La salida de `local_status.py` compartida por Santiago confirma frontend, LiveKit,
agente de voz, Qdrant, sincronización y telemetría en ejecución. Los dos
inicializadores terminaron con código 0. Es estado de servicios; no demuestra una
conversación ni labios sincronizados.

Muestra del usuario a las 12:57 del 18 de octubre, antes de arrancar Unreal:

| Servicio | RAM (MiB) | CPU Docker (%) |
| --- | ---: | ---: |
| Agente de voz | 1018 | 3,02 |
| Frontend | 75,12 | 0 |
| Telemetría | 65,38 | 0,20 |
| Sincronización | 181,8 | 0 |
| PostgreSQL | 64,69 | 0,01 |
| Qdrant | 72,77 | 0,27 |
| LiveKit | 26,77 | 0,16 |

Suma: **1504,53 MiB = 1,469 GiB**, sin incluir memoria adicional de Windows/WSL,
navegador o Unreal. El límite de 7,376 GiB de Docker no es consumo ni una reserva
por cada contenedor. La GPU RTX 4050 Laptop muestra 570 MiB de 6141 MiB y 1 % de
actividad global; incluye otras aplicaciones. D: reporta 229,14 GiB libres.
No es un benchmark ni una estimación del consumo de seis avatares.

## Implementación local

- Selector Voz/Avatar antes de conectar; Voz sigue siendo predeterminado. La misma
  sesión e identidad firmadas se mantienen, con `presentation_mode` diferenciado.
- El puente reserva un único renderer para una sala explícita. TTL de 30 segundos,
  renovación cada 5 segundos y liberación al desconectar. La prueba firmada del
  navegador dura 15 minutos; después el avatar vuelve a voz, sin cortar la llamada.
- La segunda sesión ve ocupado y puede elegir Voz. No se buscan salas ajenas en
  este modo. Los callbacks de una sala liberada se descartan y el audio se cancela.
- Las imágenes requieren una prueba de reserva en cabecera; no hay tokens en URLs.
  Se comprueba la reserva antes y después de obtener cada JPEG. La ruta antigua
  de MJPEG compartido devuelve 410. El frontend nuevo requiere el puente gestionado;
  no usarlo con el renderer histórico sin reserva.
- La captura selecciona exclusivamente la ventana del proceso de Unreal lanzado;
  no usa el escritorio ni captura audio. Envía JPEG por WebSocket al puerto local
  8766 con una clave interna. Docker solo publica ese puerto en loopback. No se
  abre un servidor de captura en la red ni se modifica el firewall.
- El audio audible permanece en LiveKit/navegador. `-VivaBrowserAudio` hace que el
  receptor nativo siga alimentando el solver y su reloj, con salida de audio local
  silenciosa. No usar `-nosound`: detendría el reloj del receptor.
- Prueba inicial de **NEXO con un solo mapa**. No se afirma cambio automático entre
  seis diseños ni que esos diseños equivalgan a seis roles. Prompts/RAG/Mem0 intactos.

## Ejecución

Docker debe estar iniciado. Guardar y cerrar Unreal antes de construir para no
copiar assets con cambios pendientes y liberar RAM. En PowerShell, una sola línea:

```powershell
python "C:\Users\santi\Edutech\Edutech\scripts\avatar_local.py" prepare
```

El proceso copia Content/Config/Plugins y el proyecto a una carpeta nueva
`D:\Edutech-Builds\nexo-<fecha>\Project`, configura el receptor y la cámara solo
en esa copia, compila y cocina el mapa de NEXO con sus dependencias. La copia
original de autoría y sus assets se conservan. No elimina construcciones anteriores.
Comprueba espacio para la copia más 50 GiB y coloca cachés/temporales en D:.
El toolchain instalado de Unreal puede seguir escribiendo logs pequeños en C:.

Después instala las herramientas de captura aisladas en D:, reconstruye únicamente
frontend/puente y sus dependencias con `compose.avatar-local.yml`, lanza el paquete
y registra 60 segundos de reposo. Cuando lo indique, abrir `http://localhost:3500`,
elegir Avatar e iniciar la llamada. El usuario concede el micrófono en su navegador.
No minimizar la ventana de Unreal durante la prueba de captura.

Ctrl+C termina los procesos de esa demo; mantiene los servicios de voz.
Para repetir una construcción ya completada:

```powershell
python "C:\Users\santi\Edutech\Edutech\scripts\avatar_local.py" run
```

## Evidencia y límites

- Construcción: `D:\Edutech-Builds\nexo-<fecha>\01-build-editor.log`,
  `02-prepare.log`, `03-package.log`, `build.json` y `Package`.
- Estado de construcción copiado a `Edutech/data/local-avatar/build-progress.json`.
- Manifest y mediciones en `Edutech/data/local-avatar/<fecha>/`: `resources.jsonl`,
  `build.json`, `unreal.log`, `capture.log`. Directorio ignorado por Git.
- Registro: RAM residente y bytes privados de Unreal, CPU acumulada del proceso,
  captura Python/FFmpeg, contenedores de esta demo, GPU global y contador de frames
  recibidos en el puente. Calcular tasas con deltas y duración real. No sumar RAM
  residente y bytes privados. CPU Docker y CPU del host tienen bases diferentes.
- Resolución solicitada 1280×720, límite nativo solicitado 30 fps, captura/petición
  web limitadas a 10 fps para esta primera prueba. Son configuración, no resultados.
  El contador JPEG mide captura/transporte al puente, no FPS renderizados o visibles.
  Unreal solicita un CSV de sus primeros 1800 frames; revisar Saved/Profiling/CSV
  del paquete para tiempos nativos y separar la carga inicial.
- Tras el primer minuto la fase se marca `interactive_unverified`: no se deduce
  que hubo habla solo por dejar el proceso abierto. Anotar inicio/fin de turnos,
  interrupción y cualquier fallo observado; repetir antes de comparar rendimiento.

Validación realizada en esta sesión: 49 pruebas del puente, 8 del frontend, 3 de
scripts (una adicional Linux omitida), TypeScript y Compose válidos. El frontend
de desarrollo respondió 200 con Voz/Avatar; sin renderer informó offline. La ruta
de frames sin prueba fue rechazada y el stream antiguo devolvió 410. Pruebas web
locales con Node 22; la imagen de producción usa Node 24.

**Pendiente:** compilar el cambio C++ y el paquete real en D:, revisar cámara y
apariencia, tres respuestas con labios, interrupción, reconexión, ausencia de eco,
segundo cliente y medición sostenida. El sandbox de esta sesión no puede acceder
al motor Docker ni escribir en D:, aunque el PowerShell del usuario sí. No se
presenta la integración nativa como ejecutada ni aceptada todavía. No hay cambios
publicados en GitHub ni despliegue a UAM.
