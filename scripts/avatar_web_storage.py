"""Local storage for the one-time avatar export. Never changes Docker or assets."""

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/local-avatar/web-storage.json"
DEFAULT_RUNTIME = (
    Path("D:/EdutechRuntime") if os.name == "nt" else ROOT / "data/local-avatar/runtime"
)


def system_root():
    """Windows' volume is independent of the location of this checkout."""
    if os.name == "nt":
        return Path(PureWindowsPath(os.environ.get("SystemRoot", "C:/Windows")).anchor)
    return Path("/")


def validate_runtime_drive(root, windows_root):
    drive = PureWindowsPath(root).drive.casefold()
    system_drive = PureWindowsPath(windows_root).drive.casefold()
    if not drive or drive == system_drive:
        raise ValueError(
            "La carpeta de trabajo debe estar en otro disco distinto del de Windows."
        )


def runtime_root():
    if CONFIG.is_file():
        return Path(json.loads(CONFIG.read_text(encoding="utf-8"))["runtime_root"])
    return DEFAULT_RUNTIME


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reject_link(path):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError(f"No se trasladan enlaces o junctions: {path}")


def snapshot(root):
    result = {}
    reject_link(root)
    for path in sorted(root.rglob("*")):
        reject_link(path)
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Ruta fuera de la carpeta esperada: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
    return result


def move_verified(source, destination, source_parent, destination_parent):
    """Copy, verify every byte via SHA-256, then remove only verified originals."""
    source, destination = Path(source), Path(destination)
    reject_link(source)
    reject_link(destination)
    expected_source = Path(source_parent).resolve() / "web-export"
    expected_destination = Path(destination_parent).resolve() / "web-export"
    if (
        source.resolve() != expected_source
        or destination.resolve() != expected_destination
    ):
        raise ValueError(
            "El traslado esta limitado a las carpetas web-export verificadas."
        )
    if destination.resolve().is_relative_to(
        source.resolve()
    ) or source.resolve().is_relative_to(destination.resolve()):
        raise ValueError("Origen y destino no pueden coincidir ni estar anidados.")
    if not source.exists():
        return {"files_moved": 0, "bytes_moved": 0, "status": "source_already_absent"}
    before = snapshot(source)
    destination.mkdir(parents=True, exist_ok=True)
    snapshot(
        destination
    )  # Reject destination links before writing through any subdirectory.
    if (
        shutil.disk_usage(destination).free
        < sum(item["bytes"] for item in before.values()) + 16 * 1024**2
    ):
        raise RuntimeError(
            "No hay espacio suficiente en el destino para copiar y verificar."
        )
    for relative, info in before.items():
        target = destination / relative
        if target.exists() and (
            not target.is_file() or digest(target) != info["sha256"]
        ):
            raise ValueError(
                f"El destino contiene un archivo diferente; se conserva el origen: {relative}"
            )
    for relative in before:
        original, target = source / relative, destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with original.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
    if snapshot(source) != before:
        raise RuntimeError(
            "Los resultados cambiaron durante la copia. No se elimina ningun original."
        )
    for relative, info in before.items():
        target = destination / relative
        if target.stat().st_size != info["bytes"] or digest(target) != info["sha256"]:
            raise RuntimeError(
                f"Fallo la verificacion de {relative}; se conservan los originales."
            )
    report = {
        "files_moved": len(before),
        "bytes_moved": sum(i["bytes"] for i in before.values()),
        "source": str(source.resolve()),
        "destination": str(destination.resolve()),
        "verified_sha256": before,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    (Path(destination_parent) / f"move-verification-{stamp}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    for relative, info in before.items():
        original = source / relative
        if digest(original) != info["sha256"]:
            raise RuntimeError(
                "Un original cambio; se detiene su retirada y la copia permanece en D:."
            )
        original.unlink()
    for path in sorted(source.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            path.rmdir()  # Only empty directories; never recursive deletion.
    source.rmdir()
    return report


def prepare(root=None):
    root = Path(root or runtime_root())
    if not root.is_absolute() or root == Path(root.anchor):
        raise ValueError("Se requiere una carpeta absoluta, no la raiz de un disco.")
    reject_link(root)
    root = root.resolve()
    if os.name == "nt":
        validate_runtime_drive(root, system_root())
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=root) as probe:
        probe.write(b"NEXO storage check")
        probe.flush()
    paths = {
        "root": root,
        "exports": root / "web-export",
        "cache": root / "DerivedDataCache",
        "user": root / "UnrealUser",
        "shaders": root / "ShaderWorkingDir",
        "temp": root / "Temp",
    }
    for path in paths.values():
        reject_link(path)
        path.mkdir(parents=True, exist_ok=True)
    return paths


def configure(root=None):
    paths = prepare(root)
    source_parent = ROOT / "data/local-avatar"
    report = move_verified(
        source_parent / "web-export", paths["exports"], source_parent, paths["root"]
    )
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    pending = CONFIG.with_suffix(".next.json")
    pending.write_text(
        json.dumps({"runtime_root": str(paths["root"]), "version": 1}, indent=2),
        encoding="utf-8",
    )
    pending.replace(CONFIG)
    print(
        f"Trasladados y verificados: {report['files_moved']} archivos, {report['bytes_moved'] / 1024**2:.2f} MiB."
    )
    print(f"Exportaciones: {paths['exports']}")
    print(f"Cache, shaders y temporales: {paths['root']}")
    print(
        "Configuracion guardada. No se ha iniciado Unreal ni modificado el proyecto original."
    )
    print(
        f"Espacio libre en el disco del sistema ({system_root()}): {shutil.disk_usage(system_root()).free / 1024**3:.2f} GiB."
    )
    print(
        f"Espacio libre en destino: {shutil.disk_usage(paths['root']).free / 1024**3:.2f} GiB."
    )


def export_environment(paths, output):
    env = dict(
        os.environ,
        NEXO_WEB_EXPORT_DIR=str(output),
        TEMP=str(paths["temp"]),
        TMP=str(paths["temp"]),
        TMPDIR=str(paths["temp"]),
    )
    env["UE-LocalDataCachePath"] = str(paths["cache"])
    flags = [
        "-DDC=InstalledNoZenLocalFallback",
        f"-LocalDataCachePath={paths['cache']}",
        f"-UserDir={paths['user']}",
        f"-ShaderWorkingDir={paths['shaders']}",
    ]
    return env, flags
