FROM ubuntu:22.04

# Xvfb + ffmpeg (con el muxer mpjpeg para servir MJPEG por HTTP directo) + las
# librerias de runtime que pide el binario empaquetado de Unreal para Linux.
# No hace falta VirtualGL: probado en vivo (2026-10-09) que el driver de
# NVIDIA presenta Vulkan directamente contra Xvfb sin el, con --gpus all +
# NVIDIA_DRIVER_CAPABILITIES=all.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb ffmpeg \
    libasound2 libpulse0 libsdl2-2.0-0 \
    libxrandr2 libxinerama1 libxcursor1 libxi6 libxv1 libxtst6 \
    libgl1 libglx-mesa0 \
    && rm -rf /var/lib/apt/lists/*

# El UID/GID real los fija `user:` en docker-compose.yml (por defecto el
# del dueno del paquete de Unreal en el host, ver mas abajo): el binario
# empaquetado escribe logs/config bajo /avatar/Avatar1/Saved, y ese volumen
# esta montado con el dueno real del host, no uno inventado aqui. UE
# ademas se niega a correr como root.
RUN mkdir -p /home/render && chmod 777 /home/render
ENV HOME=/home/render

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# El paquete de Unreal (Avatar-Package*/Linux, ~2GB) se monta como volumen en
# /avatar -- no se copia a la imagen (ver docker-compose.yml y el README de
# este directorio sobre como regenerarlo).
ENTRYPOINT ["/entrypoint.sh"]
