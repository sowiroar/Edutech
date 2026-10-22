#!/usr/bin/env python3
"""Arranque local explícito y aislado. Nunca despliega UAM ni imprime secretos."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env.voice"


def missing_settings(path=ENV):
    values = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("\"'")
    return [
        key
        for key in ("GOOGLE_API_KEY", "GEMINI_LIVE_MODEL")
        if not os.environ.get(key, values.get(key, "")).strip()
    ]


def command(action, avatar=False):
    commands = {
        "config": ["config", "--quiet"],
        "up": ["up", "-d", "--build"],
        "infra": ["up", "-d", "livekit", "qdrant"],
        "web": ["up", "-d", "--build", "frontend"],
        "ps": ["ps"],
        "down": ["down"],  # conserva volúmenes; nunca --volumes
    }
    return [
        "docker",
        "compose",
        "--project-name",
        "edutech-voice-local",
        "--env-file",
        str(ENV),
        "-f",
        str(ROOT / "compose.voice.yml"),
        *(["-f", str(ROOT / "compose.avatar-local.yml")] if avatar else []),
        *commands[action],
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("init", "doctor", "config", "infra", "web", "up", "ps", "down"),
    )
    parser.add_argument(
        "--avatar", action="store_true", help="Include the optional local avatar bridge"
    )
    args = parser.parse_args()
    if args.action == "init":
        try:
            with ENV.open("x") as dest:
                dest.write((ROOT / "voice.local.env.example").read_text())
        except FileExistsError:
            print(".env.voice ya existe; se conserva.")
        else:
            ENV.chmod(0o600)
            print("Creado .env.voice. Completa los dos campos localmente.")
        return
    if not shutil.which("docker"):
        raise SystemExit("Falta Docker/Compose. Consulta docs/mvp/RUNBOOK.md.")
    if args.action == "doctor":
        daemon = subprocess.run(["docker", "info"], capture_output=True).returncode == 0
        print("Docker disponible:", daemon)
        print("Configuración local:", ENV.is_file())
        missing = missing_settings()
        print(
            "Variables faltantes:", ", ".join(missing) or "ninguna (validez no probada)"
        )
        print("Voz requiere conexión a Google; este diagnóstico no llama al proveedor.")
        raise SystemExit(0 if daemon and ENV.is_file() and not missing else 1)
    if not ENV.is_file():
        raise SystemExit("Ejecuta primero: python3 scripts/voice_demo.py init")
    if args.action == "up" and missing_settings():
        raise SystemExit(
            "Completa GOOGLE_API_KEY y GEMINI_LIVE_MODEL en .env.voice antes de iniciar el agente."
        )
    if args.action == "up":
        from telemetry_setup import initialize

        initialize()
    runtime_env = dict(os.environ)
    if args.action in ("up", "web"):
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
        )
        if revision.returncode == 0:
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            runtime_env["APP_RELEASE"] = revision.stdout.strip() + (
                "-dirty" if dirty.stdout.strip() else ""
            )
    subprocess.run(
        command(args.action, args.avatar), cwd=ROOT, env=runtime_env, check=True
    )


if __name__ == "__main__":
    main()
