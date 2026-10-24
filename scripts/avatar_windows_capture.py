"""Capture only the launched Unreal window; send JPEGs to the loopback bridge."""

import ctypes
import subprocess
import time
from ctypes import wintypes
from pathlib import Path


def window_for_process(pid, timeout=60):
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        found = []

        @callback_type
        def inspect(hwnd, unused):
            owner, rect = wintypes.DWORD(), wintypes.RECT()
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and user.IsWindowVisible(hwnd):
                user.GetClientRect(hwnd, ctypes.byref(rect))
                if rect.right >= 640 and rect.bottom >= 360:
                    found.append(int(hwnd))
            return True

        user.EnumWindows(inspect, 0)
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            raise RuntimeError(
                "Mas de una ventana de render; no se captura el escritorio."
            )
        time.sleep(1)
    raise RuntimeError("No aparecio la ventana del ejecutable Unreal.")


def capture(pid, key, stop, log):
    import imageio_ffmpeg
    from websockets.sync.client import connect

    hwnd = window_for_process(pid)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    args = [
        ffmpeg,
        "-nostdin",
        "-loglevel",
        "warning",
        "-f",
        "gdigrab",
        "-draw_mouse",
        "0",
        "-framerate",
        "10",
        "-i",
        f"hwnd={hwnd}",
        "-vf",
        "scale=1280:720",
        "-an",
        "-threads",
        "2",
        "-f",
        "mjpeg",
        "-q:v",
        "6",
        "pipe:1",
    ]
    with Path(log).open("w") as errors:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=errors,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            with connect(
                "ws://127.0.0.1:8766/capture",
                additional_headers={"Authorization": "Bearer " + key},
                compression=None,
                max_size=1024,
            ) as socket:
                buffer = bytearray()
                while not stop.is_set():
                    chunk = process.stdout.read(65536)
                    if not chunk:
                        raise RuntimeError(f"Captura detenida. Revisa {log}")
                    buffer.extend(chunk)
                    if len(buffer) > 4 * 1024 * 1024:
                        raise RuntimeError("JPEG excede el limite")
                    while True:
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(b"\xff\xd9", start + 2) if start >= 0 else -1
                        if end < 0:
                            break
                        end += 2
                        socket.send(bytes(buffer[start:end]))
                        del buffer[:end]
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
