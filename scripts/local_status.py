"""Read-only local status: services, resource snapshot and build-drive space."""

import json
import re
import shutil
import subprocess

from voice_demo import ROOT, command


def run(args):
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def main():
    print("=== Servicios de esta demo ===", flush=True)
    result = run([*command("ps"), "--all"])
    if result is not None and result.returncode == 0:
        print(result.stdout.strip())
    else:
        print("No se pudo consultar Docker desde esta terminal.")

    print("\n=== CPU y RAM: muestra instantanea, no benchmark ===", flush=True)
    listing = run(
        [
            "docker",
            "ps",
            "--filter",
            "label=com.docker.compose.project=edutech-voice-local",
            "--format",
            "{{.ID}}",
        ]
    )
    ids = (
        []
        if listing is None or listing.returncode
        else [
            line
            for line in listing.stdout.splitlines()
            if re.fullmatch(r"[0-9a-f]{12,64}", line)
        ]
    )
    if ids:
        stats = run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}",
                *ids,
            ]
        )
        print(
            stats.stdout.strip()
            if stats is not None and stats.returncode == 0
            else "Consumo no disponible."
        )
    else:
        print("Sin contenedores consultables de esta demo; consumo desconocido.")

    print("\n=== GPU global del equipo; incluye otras aplicaciones ===", flush=True)
    if shutil.which("nvidia-smi"):
        gpu = run(
            [
                "nvidia-smi",
                "--query-gpu=timestamp,name,memory.total,memory.used,utilization.gpu",
                "--format=csv",
            ]
        )
        print(
            gpu.stdout.strip()
            if gpu is not None and gpu.returncode == 0
            else "Medicion NVIDIA no disponible."
        )
    else:
        print("nvidia-smi no disponible.")

    print("\n=== Espacio en D: ===", flush=True)
    try:
        total, used, free = shutil.disk_usage("D:\\")
        print(
            json.dumps(
                {
                    "drive": "D:",
                    "free_GiB": round(free / 2**30, 2),
                    "total_GiB": round(total / 2**30, 2),
                }
            )
        )
    except OSError:
        print("D: no accesible desde esta terminal; espacio desconocido.")


if __name__ == "__main__":
    main()
