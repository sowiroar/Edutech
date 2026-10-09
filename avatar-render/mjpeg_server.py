"""Sirve por HTTP (multipart/x-mixed-replace) los frames MJPEG que ffmpeg
manda por su stdout. Reemplaza al modo servidor nativo de ffmpeg
(`-listen 1`/`-listen 2`): probado en vivo el 2026-10-09 que `-listen 1`
solo acepta UNA conexión en toda la vida del proceso (el segundo cliente
se encuentra con "Connection refused"), y que `-listen 2` (el valor que
la ayuda de ffmpeg documenta como modo multi-cliente) acepta la conexión
TCP pero se queda colgado sin escribir nada. Un bucle que relanza ffmpeg
por cliente tampoco resultó confiable (ffmpeg no siempre termina al
desconectarse el cliente).

Este script evita el problema por completo: lanza ffmpeg UNA sola vez
para toda la vida del contenedor, lee su stdout en un hilo aparte,
guarda el último frame completo, y cada conexión HTTP nueva (tantas
como lleguen, simultáneas o en serie) recibe los frames a medida que
llegan desde ese único proceso de ffmpeg — sin ningún límite de "un
cliente a la vez" por parte del protocolo HTTP en sí (sí sigue habiendo
un solo ffmpeg/Xvfb/juego, ver README).
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
BOUNDARY = b"frame"


class FrameBroadcaster:
    """Último frame JPEG completo + un evento para avisar a quien espera uno nuevo."""

    def __init__(self) -> None:
        self._frame: bytes | None = None
        self._condition = threading.Condition()
        self._generation = 0

    def publish(self, frame: bytes) -> None:
        with self._condition:
            self._frame = frame
            self._generation += 1
            self._condition.notify_all()

    def wait_for_next(self, last_generation: int, timeout: float = 10.0) -> tuple[bytes, int] | None:
        """Bloquea hasta que haya un frame mas nuevo que `last_generation`, o hasta
        `timeout`s (para que un cliente colgado no bloquee su hilo para siempre)."""
        with self._condition:
            if not self._condition.wait_for(
                lambda: self._generation > last_generation, timeout=timeout
            ):
                return None
            return self._frame, self._generation


def read_frames(stdout, broadcaster: FrameBroadcaster) -> None:
    """ffmpeg con -f mjpeg manda JPEGs crudos, uno tras otro, sin separador
    propio: cada uno empieza en SOI (FFD8) y termina en EOI (FFD9)."""
    buffer = bytearray()
    while True:
        chunk = stdout.read(65536)
        if not chunk:
            print("[mjpeg_server] ffmpeg cerró su stdout; terminando", file=sys.stderr, flush=True)
            os._exit(1)  # que Docker reinicie el contenedor completo
        buffer.extend(chunk)
        while True:
            start = buffer.find(SOI)
            if start == -1:
                buffer.clear()
                break
            end = buffer.find(EOI, start + 2)
            if end == -1:
                if start > 0:
                    del buffer[:start]
                break
            end += 2
            broadcaster.publish(bytes(buffer[start:end]))
            del buffer[:end]


def make_handler(broadcaster: FrameBroadcaster):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silencia el access log por defecto
            pass

        def do_GET(self) -> None:
            if self.path.split("?", 1)[0] != "/stream":
                self.send_response(404)
                self.end_headers()
                return
            try:
                self.send_response(200)
                self.send_header(
                    "Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY.decode()}"
                )
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()

                generation = 0
                while True:
                    result = broadcaster.wait_for_next(generation)
                    if result is None:
                        continue  # nada nuevo todavia (timeout de espera), seguir esperando
                    frame, generation = result
                    self.wfile.write(b"--" + BOUNDARY + b"\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass  # el cliente se desconecto: nada que limpiar, solo termina este hilo

    return Handler


def main() -> None:
    display = os.environ.get("DISPLAY", ":99")
    width = os.environ.get("RENDER_WIDTH", "854")
    height = os.environ.get("RENDER_HEIGHT", "480")
    framerate = os.environ.get("STREAM_FRAMERATE", "12")
    quality = os.environ.get("STREAM_QUALITY", "10")
    port = int(os.environ.get("STREAM_PORT", "8080"))

    # -re: ver la nota larga en entrypoint.sh (git blame) -- sin esto x11grab
    # entrega muchas mas veces por segundo de lo que -framerate/-r piden.
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg", "-nostdin", "-loglevel", "warning", "-re",
            "-f", "x11grab", "-framerate", framerate, "-video_size", f"{width}x{height}", "-i", display,
            "-r", framerate, "-f", "mjpeg", "-q:v", quality, "pipe:1",
        ],
        stdout=subprocess.PIPE,
        bufsize=0,
    )
    assert ffmpeg.stdout is not None

    broadcaster = FrameBroadcaster()
    reader = threading.Thread(target=read_frames, args=(ffmpeg.stdout, broadcaster), daemon=True)
    reader.start()

    print(f"[mjpeg_server] sirviendo en :{port}/stream", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(broadcaster))
    server.daemon_threads = True
    try:
        server.serve_forever()
    finally:
        ffmpeg.terminate()


if __name__ == "__main__":
    main()
