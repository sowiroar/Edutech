# avatar-render

Pone el avatar de Unreal (video) en el frontend web, sin Pixel Streaming
(nunca llegó a verse bien en el navegador, ver historial del proyecto).
En su lugar: el juego empaquetado de Unreal corre en este contenedor contra
una pantalla virtual (Xvfb) con aceleración de GPU real, y `mjpeg_server.py`
(lanza ffmpeg internamente, lee sus frames) manda lo que se ve ahí como
MJPEG por HTTP — un `<img>` del navegador lo muestra directo, sin códecs ni
JS de video.

Probado en vivo el 2026-10-09: con `--gpus all` + `NVIDIA_DRIVER_CAPABILITIES=all`,
el driver de NVIDIA presenta Vulkan (el RHI que usa Unreal 5 en Linux) directo
contra Xvfb — **no hace falta VirtualGL**, a pesar de que en teoría Xvfb no
soporta el protocolo DRI3/Present que el driver normalmente pide. No se
investigó por qué funciona (probablemente un camino de presentación
alternativo del driver de NVIDIA); si deja de funcionar en otra versión del
driver, VirtualGL (`vglrun -d egl ...`) es el plan B — ya se confirmó que
`vglrun -d egl glxinfo`/`vulkaninfo` funcionan en este mismo contenedor base.

## El paquete de Unreal (paso manual, no está en este repo)

Este servicio NO incluye el juego: monta como volumen una carpeta generada
con `RunUAT.sh BuildCookRun`, de ~2 GB, que no tiene sentido commitear.

Regenerarla tras cualquier cambio en `Avatar/` (C++ del plugin, mapas,
actores) que deba verse reflejado en el video:

```bash
UnrealEngine/Engine/Build/BatchFiles/Linux/RunUAT.sh BuildCookRun \
  -project="<ruta>/Avatar/Avatar1.uproject" \
  -noP4 -platform=Linux -clientconfig=Development -serverconfig=Development \
  -cook -build -stage -pak -archive \
  -archivedirectory="<ruta>/Avatar-Package" \
  -unattended -utf8output
```

Sin `-map` ni `-allmaps`: solo cocina `GameDefaultMap`
(`NewMap_NEXO_Lite`, ver `Avatar/Config/DefaultEngine.ini`), que es el único
mapa que este servicio necesita. Con 32 núcleos/121 GB de RAM tardó ~15
minutos la última vez (Development, no Shipping).

`AVATAR_PACKAGE_DIR` en `.env` apunta a la carpeta `Linux/` resultante
(por defecto `../Avatar-Package/Linux`, sibling de este repo — el mismo
layout que ya usa el submódulo `Avatar/`).

## Red: por qué comparte namespace con avatar-bridge

`VivaAvatarReceiver` (C++, en el juego) solo acepta `ws://127.0.0.1:*` como
`BridgeURL` — por diseño, para no aceptar un host remoto arbitrario (ver
`Plugins/VivaAvatar/Source/VivaAvatar/Private/VivaAvatarReceiver.cpp`). Por
eso este servicio usa `network_mode: "service:avatar-bridge"` en vez de su
propia red: comparte el loopback de `avatar-bridge`, así que
`ws://127.0.0.1:8766` adentro del juego es de verdad `avatar-bridge:8766`.

Consecuencia práctica: este servicio **no tiene su propio hostname ni
puertos publicados** — el stream MJPEG se expone en el puerto de
`avatar-bridge` (ver `STREAM_PORT` y el `ports:` de `avatar-bridge` en
`docker-compose.yml`), y el frontend lo alcanza como
`http://avatar-bridge:${STREAM_PORT}/stream`, nunca como
`http://avatar-render:...`.

## Variables de entorno

| Variable | Default | Qué hace |
| --- | --- | --- |
| `RENDER_WIDTH`/`RENDER_HEIGHT` | 854/480 | Resolución de Xvfb y del juego. |
| `STREAM_FRAMERATE` | 12 | FPS del MJPEG (no el FPS del juego). |
| `STREAM_QUALITY` | 10 | Calidad JPEG de ffmpeg (2 mejor .. 31 peor). Más alta = más ancho de banda. |
| `STREAM_PORT` | 8080 | Puerto donde `mjpeg_server.py` sirve `/stream`. |

MJPEG no comprime entre frames (cada uno es un JPEG independiente, a diferencia de un
códec real como H.264). Con los defaults (480p/calidad 10/12fps), probado en vivo:
~385 KB/s (~3.1 Mbit/s) en régimen estable, ~12.4 fps reales. Subir resolución/calidad si
el ancho de banda no es problema.

`-re` en ffmpeg (leer la entrada "a su ritmo nativo") es necesario: sin él, x11grab entrega
frames mucho más rápido que `-framerate`/`-r` (probado: ~100 fps reales con
`STREAM_FRAMERATE=12`, 8x más ancho de banda). Incluso con `-re`, los primeros segundos
después de que arranca el contenedor (o de que se conecta el primer espectador tras un
rato sin ninguno) salen con una ráfaga de frames más rápida de lo normal mientras drena un
colchón interno de ffmpeg; se estabiliza solo al ritmo configurado en unos 10-15s.

## Por qué `mjpeg_server.py` y no el servidor HTTP de ffmpeg directo

El primer intento usaba `ffmpeg -f mpjpeg -listen 1 http://0.0.0.0:8080/stream`
directo, sin nada más — funcionaba para una sola conexión manual, pero falló en
vivo con el frontend real:

- `-listen 1` (el valor documentado como "modo servidor") solo acepta **una
  conexión en toda la vida del proceso**: la segunda pestaña/recarga del
  frontend se encontró con `Connection refused`.
- `-listen 2` (el valor que la ayuda de ffmpeg documenta como modo
  multi-cliente) acepta la conexión TCP pero se queda colgado sin escribir
  nada — confirmado en vivo, 0 bytes en varios segundos.
- Un bucle de bash relanzando ffmpeg por cada cliente tampoco resultó
  confiable: ffmpeg no siempre termina limpio cuando el cliente se
  desconecta.

`mjpeg_server.py` evita todo esto: lanza ffmpeg **una sola vez** para toda la
vida del contenedor (sin `-listen`, solo `-f mjpeg pipe:1`), lee sus frames
por stdin, y un servidor HTTP propio (`http.server.ThreadingHTTPServer`, un
hilo por conexión) los reparte a cuantos clientes se conecten — simultáneos o
en serie, sin el límite de "un cliente a la vez" de arriba. Coherente con el
resto del sistema de todas formas (`avatar-bridge` sigue pensado para una
sola persona usando la app a la vez, ver su README), pero ya no es una
limitación extra de esta pieza en particular.

## Verificación manual

```bash
docker compose up -d avatar-render
# AVATAR_STREAM_PORT (default 8080), publicado en avatar-bridge porque
# avatar-render comparte su red (ver arriba):
curl -sv http://127.0.0.1:8080/stream -o /tmp/avatar.mjpeg
```

O simplemente abrir `http://127.0.0.1:8080/stream` en el navegador: debe
verse el video actualizándose solo (sin controles, porque es una secuencia
de imágenes, no un `<video>`). En la app, es `/api/avatar/stream`
(`agent-starter-react`) el que lo reenvía: ver `AVATAR_STREAM_SOURCE_URL`.
