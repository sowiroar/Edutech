"""Build NEXO on D: in a fresh copy. Never changes original assets or deletes builds."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "Avatar"
ENGINE = Path(r"C:\Program Files\Epic Games\UE_5.8")


def command(engine, project, output, scene):
    return [
        str(engine / "Engine/Build/BatchFiles/RunUAT.bat"),
        "BuildCookRun",
        f"-project={project / 'Avatar1.uproject'}",
        "-noP4",
        "-platform=Win64",
        "-clientconfig=Development",
        "-build",
        "-cook",
        "-stage",
        "-pak",
        "-package",
        "-archive",
        f"-archivedirectory={output}",
        f"-map={scene}",
        "-unattended",
        "-utf8output",
        "-UbtArgs=-MaxParallelActions=2",
    ]


def run_logged(args, cwd, env, log):
    print(f"Proceso en curso. Registro: {log}", flush=True)
    progress = ROOT / "data/local-avatar/build-progress.json"
    progress.parent.mkdir(parents=True, exist_ok=True)
    progress.write_text(
        json.dumps({"phase": log.stem, "status": "running", "log": str(log)})
    )
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            args, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT
        )
    progress.write_text(
        json.dumps(
            {
                "phase": log.stem,
                "status": "finished" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "log": str(log),
                "tail": log.read_text(encoding="utf-8", errors="replace").splitlines()[
                    -25:
                ],
            }
        )
    )
    if result.returncode:
        # Build output does not contain .env or provider credentials.
        print(
            "\n".join(
                log.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
            )
        )
        raise RuntimeError(f"No se completo este paso. Registro: {log}")


def build(destination, engine=ENGINE):
    if os.name != "nt":
        raise RuntimeError("This build requires Windows and Unreal 5.8")
    destination = destination.resolve()
    if destination.drive.lower() == SOURCE.drive.lower():
        raise RuntimeError("Usa D:; C: no tiene espacio para esta construccion.")
    editor = engine / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
    if not editor.is_file() or not (SOURCE / "Avatar1.uproject").is_file():
        raise RuntimeError("No se encuentra Unreal o el proyecto Avatar.")
    # Checking process names does not stop or control the editor.
    opened = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/NH"],
        capture_output=True,
        text=True,
    )
    if opened.returncode == 0 and "UnrealEditor.exe" in opened.stdout:
        raise RuntimeError(
            "Guarda y cierra Unreal antes de construir, para liberar RAM y copiar assets guardados."
        )
    destination.mkdir(parents=True, exist_ok=True)
    essential = [
        SOURCE / name
        for name in ("Content", "Config", "Plugins", "Source")
        if (SOURCE / name).is_dir()
    ]
    source_bytes = sum(
        p.stat().st_size
        for directory in essential
        for p in directory.rglob("*")
        if p.is_file()
    )
    if shutil.disk_usage(destination).free < source_bytes + 50 * 1024**3:
        raise RuntimeError(
            "D: necesita espacio para copiar el proyecto y al menos 50 GiB adicionales para compilar."
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run = destination / ("nexo-" + stamp)
    run.mkdir(exist_ok=False)
    project, output, cache = run / "Project", run / "Package", run / "Cache"
    project.mkdir()
    cache.mkdir()
    print(f"Copiando proyecto a {project}. Original conservado.", flush=True)
    for directory in essential:
        shutil.copytree(
            directory,
            project / directory.name,
            ignore=shutil.ignore_patterns(
                "Intermediate", "DerivedDataCache", "__pycache__"
            ),
        )
    for name in ("Avatar1.uproject", "avatars.json"):
        shutil.copy2(SOURCE / name, project / name)
    # Preserve compiled editor modules if available; UAT builds the runtime modules.
    if (SOURCE / "Binaries").is_dir():
        shutil.copytree(SOURCE / "Binaries", project / "Binaries")
    (project / ".viva-local-build").write_text("disposable copy\n")
    env = dict(os.environ)
    for variable in (
        "TEMP",
        "TMP",
        "UE-LocalDataCachePath",
        "UE-SharedDataCachePath",
        "UE-ZenDataPath",
    ):
        folder = cache / variable.replace("UE-", "")
        folder.mkdir(exist_ok=True)
        env[variable] = str(folder)
    env["VIVA_BUILD_PROJECT"] = str(project)
    # Use the newly compiled opt-in browser-audio receiver in this isolated copy.
    descriptor = json.loads(
        (project / "Avatar1.uproject").read_text(encoding="utf-8-sig")
    )
    for plugin in descriptor["Plugins"]:
        if plugin["Name"] in ("ModelContextProtocol", "AllToolsets"):
            plugin["Enabled"] = False
    (project / "Avatar1.uproject").write_text(
        json.dumps(descriptor, indent=2), encoding="utf-8"
    )
    # Build the editor target before Python adds its receiver; UAT generates a temporary target for this BP project.
    uat = engine / "Engine/Build/BatchFiles/RunUAT.bat"
    run_logged(
        [
            str(uat),
            "BuildCookRun",
            f"-project={project / 'Avatar1.uproject'}",
            "-noP4",
            "-platform=Win64",
            "-build",
            "-skipcook",
            "-unattended",
            "-UbtArgs=-MaxParallelActions=2",
        ],
        project,
        env,
        run / "01-build-editor.log",
    )
    run_logged(
        [
            str(editor),
            str(project / "Avatar1.uproject"),
            "-unattended",
            "-nosplash",
            "-run=pythonscript",
            f"-script={ROOT / 'scripts/prepare_nexo_local.py'}",
            "-stdout",
            "-FullStdOutLogOutput",
        ],
        project,
        env,
        run / "02-prepare.log",
    )
    marker = project / "prepared.json"
    if not marker.is_file():
        raise RuntimeError("La preparacion no produjo su comprobante; no se empaqueta.")
    scene = json.loads(marker.read_text())["map"]
    run_logged(
        command(engine, project, output, scene), project, env, run / "03-package.log"
    )
    candidates = list(output.glob("Windows/Avatar1/Binaries/Win64/Avatar1*.exe"))
    cooked = list(output.glob("Windows/Avatar1/Content/Paks/*.pak"))
    if len(candidates) != 1 or not cooked:
        raise RuntimeError("El paquete no contiene ejecutable y contenido completos.")
    profile = json.loads((project / "Config/Profiles/lira-efficient.json").read_text())
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE, capture_output=True, text=True
    )
    result = {
        "exe": str(candidates[0]),
        "project": str(project),
        "scene": scene,
        "design": "nexo-design",
        "profile": profile,
        "configuration": "Win64 Development",
        "avatar_revision": revision.stdout.strip(),
        "local_changes_included": True,
        "validation": "built; conversation, lip sync and performance pending",
    }
    (run / "build.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    evidence = ROOT / "data/local-avatar"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "build.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Paquete construido: {candidates[0]}", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path("D:/Edutech-Builds"))
    args = parser.parse_args()
    try:
        build(args.destination)
    except (OSError, RuntimeError) as exc:
        sys.exit(str(exc))
