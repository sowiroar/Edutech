"""One-line local setup/build/run for the optional NEXO proof on D:."""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from voice_demo import ROOT


def env_values():
    values = {}
    for line in (ROOT / ".env.voice").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def install_tools(destination):
    tools = destination / "capture-tools"
    python = tools / "Scripts/python.exe"
    if not python.is_file():
        subprocess.run(
            [sys.executable, "-m", "venv", "--without-pip", str(tools)], check=True
        )
    env = dict(
        os.environ,
        PIP_CACHE_DIR=str(destination / "pip-cache"),
        TMP=str(destination),
        TEMP=str(destination),
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "--python",
            str(python),
            "install",
            "imageio-ffmpeg==0.6.0",
            "websockets>=15,<16",
            "psutil>=7,<8",
        ],
        env=env,
        check=True,
    )
    return python


def request(path, key=""):
    req = urllib.request.Request(
        "http://127.0.0.1:8766" + path, headers={"Authorization": "Bearer " + key}
    )
    with urllib.request.urlopen(req, timeout=2) as response:
        return json.load(response)


def measurement(process, key, elapsed, label):
    import psutil

    proc = psutil.Process(process.pid)
    memory = proc.memory_info()
    info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "phase": label,
        "pid": process.pid,
        "unreal_working_set_bytes": memory.rss,
        "unreal_private_bytes": getattr(memory, "private", None),
        "unreal_cpu_seconds": sum(proc.cpu_times()[:2]),
    }
    launcher = psutil.Process()
    info["capture_launcher_working_set_bytes"] = launcher.memory_info().rss
    info["capture_workers"] = []
    for child in launcher.children(recursive=True):
        try:
            if child.name().lower().startswith("ffmpeg"):
                info["capture_workers"].append(
                    {
                        "pid": child.pid,
                        "working_set_bytes": child.memory_info().rss,
                        "cpu_seconds": sum(child.cpu_times()[:2]),
                    }
                )
        except psutil.Error:
            pass
    try:
        listing = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "label=com.docker.compose.project=edutech-voice-local",
                "--format",
                "{{.ID}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        ids = listing.stdout.split() if listing.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        ids = []
    for field, args in (
        (
            "containers",
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", *ids]
            if ids
            else None,
        ),
        (
            "gpu_global",
            [
                "nvidia-smi",
                "--query-gpu=timestamp,name,driver_version,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader",
            ],
        ),
    ):
        try:
            if args is None:
                info[field] = None
                continue
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            info[field] = result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            info[field] = None
    try:
        info["capture"] = request("/render/health", key)
    except Exception:
        info["capture"] = None
    return info


def run_demo():
    from avatar_windows_capture import capture

    build = json.loads(
        (ROOT / "data/local-avatar/build.json").read_text(encoding="utf-8")
    )
    exe = Path(build["exe"])
    if not exe.is_file():
        raise RuntimeError("Falta el paquete: ejecuta primero avatar_local.py prepare")
    key = env_values().get("TELEMETRY_INTERNAL_KEY", "")
    if len(key) < 32:
        raise RuntimeError("Falta configuracion local del puente.")
    if request("/status").get("unreal_connected"):
        raise RuntimeError(
            "Ya hay otro Unreal conectado; cierra esa demo antes de iniciar otra."
        )
    evidence = (
        ROOT
        / "data/local-avatar"
        / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    )
    evidence.mkdir(parents=True, exist_ok=False)
    (evidence / "build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
    args = [
        str(exe),
        build["scene"],
        "-windowed",
        "-ResX=1280",
        "-ResY=720",
        "-NoSplash",
        "-VivaBrowserAudio",
        "-csvCaptureFrames=1800",
        "-ExecCmds=t.MaxFPS 30",
        f"-abslog={evidence / 'unreal.log'}",
        *[f"-ini:Engine:[SystemSettings]:{k}={v}" for k, v in build["profile"].items()],
    ]
    process = subprocess.Popen(args, cwd=exe.parent)
    stop = threading.Event()
    workers = ThreadPoolExecutor(max_workers=1)
    capture_task = workers.submit(
        capture, process.pid, key, stop, evidence / "capture.log"
    )
    try:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"Unreal termino. Registro: {evidence / 'unreal.log'}"
                )
            if capture_task.done():
                capture_task.result()
            status, frames = request("/status"), request("/render/health", key)
            if status.get("unreal_connected") and frames.get("ready"):
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"No se completo la conexion/captura. Revisa {evidence}")
        print(
            "NEXO conectado. Midiendo 60 segundos de reposo; espera antes de iniciar la llamada.",
            flush=True,
        )
        started = time.monotonic()
        with (evidence / "resources.jsonl").open("w", encoding="utf-8") as stream:
            announced = False
            while process.poll() is None:
                if capture_task.done():
                    capture_task.result()
                elapsed = time.monotonic() - started
                if elapsed >= 60 and not announced:
                    print(
                        "Ahora abre http://localhost:3500, elige Avatar e inicia tu llamada. Se sigue midiendo.",
                        flush=True,
                    )
                    print(
                        f"Resultados: {evidence}\nCtrl+C termina esta demo; los servicios de voz permanecen.",
                        flush=True,
                    )
                    announced = True
                sample = measurement(
                    process,
                    key,
                    elapsed,
                    "idle" if elapsed < 60 else "interactive_unverified",
                )
                stream.write(json.dumps(sample) + "\n")
                stream.flush()
                time.sleep(3)
    finally:
        stop.set()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        workers.shutdown(wait=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    raise RuntimeError(
        "Flujo nativo suspendido. La entrega vigente usa avatar_web.py para exportar una sola vez y dibujar el modelo en el navegador; no iniciar renderer ni captura."
    )
    if os.name != "nt":
        raise RuntimeError("La prueba requiere Windows.")
    if args.action == "prepare":
        raise RuntimeError(
            "Flujo nativo suspendido: se esta preparando el avatar para renderizar directamente en el navegador, segun la nueva indicacion. No construyas Unreal para esta prueba."
        )
        subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], check=True)
        from avatar_windows_build import build

        destination = Path("D:/Edutech-Builds")
        build(destination)
        python = install_tools(destination)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/voice_demo.py"), "--avatar", "web"],
            check=True,
        )
        subprocess.run([str(python), str(Path(__file__).resolve()), "run"], check=True)
    else:
        if (
            importlib.util.find_spec("psutil") is None
            or importlib.util.find_spec("imageio_ffmpeg") is None
        ):
            python = Path("D:/Edutech-Builds/capture-tools/Scripts/python.exe")
            if python.is_file():
                subprocess.run(
                    [str(python), str(Path(__file__).resolve()), "run"], check=True
                )
                return
            raise RuntimeError("Ejecuta primero avatar_local.py prepare")
        run_demo()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Demo terminada.")
    except Exception as exc:
        sys.exit(str(exc))
