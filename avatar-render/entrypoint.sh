#!/bin/bash
# Arranca Xvfb, el juego empaquetado de Unreal (apuntando a avatar-bridge por
# loopback, ver docker-compose.yml) y mjpeg_server.py (lanza ffmpeg internamente
# y reparte lo que se ve por HTTP como MJPEG — multipart/x-mixed-replace, lo
# que entiende un <img> del navegador sin JS extra). Probado en vivo el
# 2026-10-09: con --gpus all + NVIDIA_DRIVER_CAPABILITIES=all, Vulkan presenta
# GPU-acelerado directo contra Xvfb, sin VirtualGL.
set -euo pipefail

: "${DISPLAY:=:99}"
: "${RENDER_WIDTH:=1280}"
: "${RENDER_HEIGHT:=720}"
: "${STREAM_FRAMERATE:=15}"
: "${STREAM_QUALITY:=6}"   # ffmpeg -q:v para mjpeg: 2 (mejor) .. 31 (peor)
: "${STREAM_PORT:=8080}"
: "${AVATAR_BIN:=/avatar/Avatar1.sh}"

export DISPLAY RENDER_WIDTH RENDER_HEIGHT STREAM_FRAMERATE STREAM_QUALITY STREAM_PORT

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
    kill "$GAME_PID" "$XVFB_PID" "${SERVER_PID:-}" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Esperar a que el juego realmente dibuje algo antes de arrancar el server (si
# arranca contra una ventana vacia, el primer rato de stream sale en negro).
sleep 12

echo "[avatar-render] arrancando mjpeg_server.py"
# ffmpeg con su propio -listen como servidor HTTP resultó poco confiable
# (ver mjpeg_server.py para el detalle: -listen 1 solo sirve UN cliente en
# toda la vida del proceso, -listen 2 se cuelga sin escribir nada). Este
# script lanza ffmpeg una sola vez, le lee el MJPEG crudo por su stdout, y
# el servidor HTTP lo reparte el mismo — sin ese límite.
python3 /mjpeg_server.py &
SERVER_PID=$!

# Si cualquiera de los tres muere, salir (y que Docker reinicie el
# contenedor entero en vez de quedar a medias sirviendo nada util).
wait -n "$GAME_PID" "$XVFB_PID" "$SERVER_PID"
