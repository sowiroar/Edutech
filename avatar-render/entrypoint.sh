#!/bin/bash
# Arranca Xvfb, el juego empaquetado de Unreal (apuntando a avatar-bridge por
# loopback, ver docker-compose.yml) y ffmpeg sirviendo lo que se ve ahi como
# MJPEG por HTTP (multipart/x-mixed-replace, lo que entiende un <img> del
# navegador sin JS extra). Probado en vivo el 2026-10-09: con --gpus all +
# NVIDIA_DRIVER_CAPABILITIES=all, Vulkan presenta GPU-acelerado directo
# contra Xvfb, sin VirtualGL.
set -euo pipefail

: "${DISPLAY:=:99}"
: "${RENDER_WIDTH:=1280}"
: "${RENDER_HEIGHT:=720}"
: "${STREAM_FRAMERATE:=15}"
: "${STREAM_QUALITY:=6}"   # ffmpeg -q:v para mjpeg: 2 (mejor) .. 31 (peor)
: "${STREAM_PORT:=8080}"
: "${AVATAR_BIN:=/avatar/Avatar1.sh}"

export DISPLAY

echo "[avatar-render] arrancando Xvfb en $DISPLAY (${RENDER_WIDTH}x${RENDER_HEIGHT})"
Xvfb "$DISPLAY" -screen 0 "${RENDER_WIDTH}x${RENDER_HEIGHT}x24" -nolisten tcp &
XVFB_PID=$!

# Esperar el socket real de Xvfb en vez de un sleep fijo: arranca casi
# siempre en bajo un segundo, pero no hay garantia bajo carga.
for _ in $(seq 1 50); do
    if [ -e "/tmp/.X11-unix/X${DISPLAY#:}" ]; then
        break
    fi
    sleep 0.2
done

echo "[avatar-render] lanzando el juego ($AVATAR_BIN)"
"$AVATAR_BIN" -game -NoSplash -log -ResX="$RENDER_WIDTH" -ResY="$RENDER_HEIGHT" -windowed -ForceRes &
GAME_PID=$!

cleanup() {
    echo "[avatar-render] cerrando..."
    kill "$GAME_PID" "$XVFB_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Esperar a que el juego realmente dibuje algo antes de arrancar ffmpeg (si
# arranca contra una ventana vacia, el primer rato de stream sale en negro).
sleep 12

echo "[avatar-render] sirviendo MJPEG en :$STREAM_PORT/stream"
# -listen 1: ffmpeg mismo hace de servidor HTTP (sin proceso aparte). Si el
# juego muere, esto se cae con el -> el contenedor termina -> Docker lo
# reinicia completo (restart: unless-stopped en docker-compose.yml).
# -framerate en la entrada de x11grab (y -r de salida, probado tambien)
# NO alcanzan para limitar el ritmo real de entrega: sin -re salian ~100
# fps de verdad con STREAM_FRAMERATE=12 (8x el ancho de banda esperado) --
# x11grab no se bloquea solo al ritmo real, solo cuenta/descarta frames
# logicos, pero los escribe a la red tan rapido como los procesa. -re
# ("leer la entrada a su ritmo nativo") es lo que de verdad lo pausa al
# ritmo real (confirmado en vivo el 2026-10-09).
ffmpeg -nostdin -loglevel warning -re \
    -f x11grab -framerate "$STREAM_FRAMERATE" -video_size "${RENDER_WIDTH}x${RENDER_HEIGHT}" -i "$DISPLAY" \
    -r "$STREAM_FRAMERATE" -f mpjpeg -q:v "$STREAM_QUALITY" \
    -listen 1 "http://0.0.0.0:${STREAM_PORT}/stream" &
FFMPEG_PID=$!

# Si cualquiera de los tres procesos muere, salir (y que el contenedor
# completo se reinicie en vez de quedar a medias sirviendo nada util).
wait -n "$GAME_PID" "$XVFB_PID" "$FFMPEG_PID"
