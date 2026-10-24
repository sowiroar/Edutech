"""One-time Unreal -> browser export; never starts a streaming renderer or Docker."""

import argparse
import hashlib
import json
import math
import os
import shutil
import signal
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 20 * 1024 * 1024
MAX_TRIANGLES = 100_000
CHARACTERS = ("NEXO", "LIRA", "ELIAN", "NOA", "NOVA", "ATLAS")


def export_failure(export_dir, returncode):
    """Show the actual script error instead of only Windows' unsigned -1."""
    log = export_dir / "console.log"
    details = []
    if log.is_file():
        with log.open("rb") as stream:
            stream.seek(max(0, log.stat().st_size - 256 * 1024))
            lines = stream.read().decode("utf-8", errors="replace").splitlines()
        for line in lines:
            if "LogPython: Error:" in line:
                message = line.split("LogPython: Error:", 1)[1].strip()
                if message and message not in details:
                    details.append(message)
    cause = "\n" + "\n".join(details[-8:]) if details else ""
    return f"Unreal no completo la exportacion (codigo {returncode}).{cause}\nRevisa {export_dir}"


def validate_export_files(export_dir, character, *, require_native_face=True):
    """A report alone is not success: Unreal can exit zero after script failures."""
    names = ["export.json", f"{character.lower()}-source.glb"]
    if character == "LIRA":
        names += ["lira-brows.glb", "lira-brows-attribute.tga"]
    elif character in ("ELIAN", "NOA", "NOVA", "ATLAS"):
        sections = 7 if character in ("NOA", "NOVA") else 4
        names += [
            f"{character.lower()}-face-material-{i}.glb" for i in range(1, sections)
        ]
    elif character == "NEXO":
        names += ["nexo-original-color.glb"]
        if require_native_face:
            names += ["nexo-native-lod3.glb", "native-face.json"]
    missing = [
        name
        for name in names
        if not (export_dir / name).is_file() or (export_dir / name).stat().st_size == 0
    ]
    if missing:
        raise ValueError("Exportacion incompleta; no se instala: " + ", ".join(missing))


def inspect_glb(path):
    data = path.read_bytes()
    if len(data) < 20 or len(data) > MAX_BYTES:
        raise ValueError(
            "Modelo fuera del presupuesto web de 20 MiB; necesita optimizacion."
        )
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("GLB incompleto o invalido.")
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A or 20 + chunk_length > len(data):
        raise ValueError("Falta la descripcion glTF.")
    doc = json.loads(data[20 : 20 + chunk_length])
    if any(
        item.get("uri") for kind in ("buffers", "images") for item in doc.get(kind, [])
    ):
        raise ValueError(
            "La entrega web debe contener todas sus texturas y buffers en el GLB."
        )
    supported = {
        "KHR_mesh_quantization",
        "KHR_materials_unlit",
        "KHR_materials_clearcoat",
        "KHR_materials_transmission",
        "KHR_materials_ior",
        "KHR_materials_specular",
        "KHR_materials_volume",
        "KHR_materials_sheen",
        "KHR_materials_emissive_strength",
        "KHR_texture_transform",
        "KHR_materials_iridescence",
        "KHR_materials_anisotropy",
    }
    if set(doc.get("extensionsRequired", [])) - supported:
        raise ValueError("El GLB requiere un decodificador no incluido en el visor.")
    triangles = 0
    for node in doc.get("nodes", []):
        if "mesh" not in node:
            continue
        for primitive in doc["meshes"][node["mesh"]]["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError("Se requieren triangulos para medir el presupuesto.")
            accessor = primitive.get("indices", primitive["attributes"]["POSITION"])
            triangles += doc["accessors"][accessor]["count"] // 3
    if not 0 < triangles <= MAX_TRIANGLES:
        raise ValueError(f"Geometria fuera del presupuesto: {triangles} triangulos.")
    if not doc.get("skins"):
        raise ValueError("No se exporto el esqueleto del personaje.")
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "triangles": triangles,
        "skins": len(doc["skins"]),
        "joints": sum(len(s["joints"]) for s in doc["skins"]),
        "animations": len(doc.get("animations", [])),
        "mouthMorphCandidates": sorted(
            {
                name
                for mesh in doc.get("meshes", [])
                for name in mesh.get("extras", {}).get("targetNames", [])
                if "jaw" in name.lower() or "mouth" in name.lower()
            }
        ),
    }


def install(export_dir, *, preview_only=False):
    report = json.loads((export_dir / "export.json").read_text(encoding="utf-8"))
    character = report.get("character", "NEXO")
    if character not in CHARACTERS:
        raise ValueError("Personaje de exportacion desconocido.")
    validate_export_files(export_dir, character)
    slug = character.lower()
    if report.get("saved_authoring_assets") is not False or not math.isfinite(
        report["frontYaw"]
    ):
        raise ValueError("El informe de exportacion no es valido.")
    if report.get("export_profile", 1) < 3:
        raise ValueError(
            "Este archivo usa el exportador de buffers con pesos de piel invalidos. Necesita perfil 3 (malla fuente)."
        )
    from optimize_nexo_glb import optimize

    source = export_dir / f"{slug}-web.glb"
    optimization = optimize(
        export_dir / f"{slug}-source.glb",
        source,
        legacy_materials=report.get("export_profile", 1) == 1,
        skin_roles=report.get("skin_roles"),
        character=character,
    )
    (export_dir / "optimization.json").write_text(
        json.dumps(optimization, indent=2), encoding="utf-8"
    )
    info = inspect_glb(source)
    background = ROOT.parent / "Avatar/Uam-virtual.jpg"
    if not background.is_file():
        raise FileNotFoundError("No se encontro Uam-virtual.jpg en Avatar.")
    public = ROOT / "agent-starter-react/public/avatars" / slug
    public.mkdir(parents=True, exist_ok=True)
    destination = public / f"{slug}-{info['sha256']}.glb"
    if not destination.exists():
        shutil.copyfile(source, destination)
    background_dest = public / (
        "uam-background.preview.jpg" if preview_only else "uam-background.jpg"
    )
    if background_dest.exists():
        shutil.copyfile(
            background_dest,
            export_dir
            / (
                "previous-preview-background.jpg"
                if preview_only
                else "previous-background.jpg"
            ),
        )
    shutil.copyfile(background, background_dest)
    manifest = public / ("manifest.preview.json" if preview_only else "manifest.json")
    if manifest.exists():
        shutil.copyfile(
            manifest,
            export_dir
            / (
                "previous-preview-manifest.json"
                if preview_only
                else "previous-manifest.json"
            ),
        )
    info.update(
        character=character,
        source_scene=report.get("scene"),
        source_author=report.get("source_author"),
        frontYaw=report["frontYaw"],
        visual_review="pending",
        motion_review="pending",
        mouth_mapping="pending",
        web_profile=2,
        export_profile=report.get("export_profile", 1),
    )
    if report.get("background_color"):
        info["background_color"] = report["background_color"]
    if report.get("background_source"):
        info["background_source"] = report.get("background_source")
    if optimization["has_mouth_rig"]:
        info["rigProfile"] = (
            "metahuman-mateo-web-v1" if character == "NEXO" else "metahuman-web-v1"
        )
    temp = public / (
        "manifest.preview.next.json" if preview_only else "manifest.next.json"
    )
    temp.write_text(json.dumps(info, indent=2), encoding="utf-8")
    temp.replace(manifest)
    (
        export_dir / ("installed-preview.json" if preview_only else "installed.json")
    ).write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(
        f"Modelo instalado: {info['bytes'] / 1048576:.1f} MiB, {info['triangles']} triangulos."
    )
    print(
        "Pendiente revisar apariencia, ropa y movimiento en /avatar-preview. No es una validacion de lip sync."
    )


def editor_path():
    override = os.environ.get("UNREAL_EDITOR_CMD")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path(
            "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd"
        )
    if os.name == "nt":
        return Path(
            "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
        )
    raise RuntimeError("Indica UNREAL_EDITOR_CMD para este sistema.")


def process_options():
    return (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )


def stop_export(process):
    """Stop only the child group created by this invocation, including shader workers."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
        except ProcessLookupError:
            pass


def export(character="NEXO", *, install_result=True):
    project = ROOT.parent / "Avatar/Avatar1.uproject"
    editor = editor_path()
    if not project.is_file() or not editor.is_file():
        raise FileNotFoundError("No se encuentra el proyecto o Unreal Engine 5.8.")
    from avatar_web_storage import export_environment, prepare, system_root

    paths = prepare()
    if shutil.disk_usage(paths["root"]).free < 10 * 1024**3:
        raise RuntimeError(
            "El disco de exportacion necesita al menos 10 GiB libres para sus temporales."
        )
    if shutil.disk_usage(system_root()).free < 1024**3:
        raise RuntimeError(
            f"El disco del sistema ({system_root()}) necesita al menos 1 GiB libre para el sistema. No se inicia Unreal."
        )
    export_dir = paths["exports"] / (
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        + ("-" + character.lower() if character != "NEXO" else "")
    )
    export_dir.mkdir(parents=True, exist_ok=False)
    runtime_env, storage_flags = export_environment(paths, export_dir)
    runtime_env["VIVA_WEB_CHARACTER"] = character
    exporter = (
        "export_family_web.py"
        if character in ("NOA", "NOVA", "ATLAS")
        else "export_" + character.lower() + "_web.py"
    )
    args = [
        str(editor),
        str(project),
        "-EnablePlugins=GLTFExporter",
        "-run=pythonscript",
        f"-script={ROOT / 'scripts' / exporter}",
        "-AllowCommandletRendering",
        "-unattended",
        "-NoSplash",
        "-nosound",
        "-stdout",
        "-FullStdOutLogOutput",
        f"-abslog={export_dir / 'unreal.log'}",
        *storage_flags,
    ]
    # Hair/face textures can exhaust Windows commit when compiled concurrently.
    # These process-only flags do not alter the authoring project's settings.
    if character in CHARACTERS:
        args += [
            "-asyncTextureCompilationMaxConcurrency=1",
            "-asyncSkeletalMeshCompilationMaxConcurrency=1",
            "-asyncStaticMeshCompilationMaxConcurrency=1",
            "-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=8",
            "-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreadsDuringGame=8",
        ]
    print(
        "Exportando una sola vez. Unreal se cerrara al terminar; el navegador usara el archivo GLB.",
        flush=True,
    )
    print(f"Registros: {export_dir}", flush=True)
    with (export_dir / "console.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            args,
            cwd=editor.parent,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=runtime_env,
            **process_options(),
        )
        started = time.monotonic()
        try:
            while process.poll() is None:
                if time.monotonic() - started > 1800:
                    raise RuntimeError(
                        f"La exportacion excedio 30 minutos. Revisa {export_dir}"
                    )
                time.sleep(1)
        finally:
            if process.poll() is None:
                stop_export(process)
    if process.returncode or not (export_dir / "export.json").is_file():
        raise RuntimeError(export_failure(export_dir, process.returncode))
    validate_export_files(export_dir, character, require_native_face=False)
    if character == "NEXO":
        print(
            "Recuperando el rostro nativo LOD3 sin abrir el editor ni guardar assets.",
            flush=True,
        )
        native_args = [
            str(editor),
            str(project),
            "-EnablePlugins=GLTFExporter,MetaHumanSDK",
            "-run=pythonscript",
            f"-script={ROOT / 'scripts/export_nexo_native_face.py'}",
            "-nullrhi",
            "-unattended",
            "-NoSplash",
            "-nosound",
            "-stdout",
            "-FullStdOutLogOutput",
            f"-abslog={export_dir / 'native-face-unreal.log'}",
            *storage_flags,
        ]
        with (export_dir / "native-face-console.log").open("w", encoding="utf8") as log:
            process = subprocess.Popen(
                native_args,
                cwd=editor.parent,
                env=runtime_env,
                stdout=log,
                stderr=subprocess.STDOUT,
                **process_options(),
            )
            try:
                code = process.wait(timeout=600)
            finally:
                if process.poll() is None:
                    stop_export(process)
        if code or not (export_dir / "native-face.json").is_file():
            raise RuntimeError(
                f"El rostro nativo no se exporto; se conserva el modelo instalado. Revisa {export_dir / 'native-face-console.log'}"
            )
    validate_export_files(export_dir, character)
    if install_result:
        install(export_dir)
    else:
        print(f"Candidato exportado sin instalar: {export_dir}", flush=True)
    return export_dir


def cancel():
    """Stop only this script's export child, after validating its full command line."""
    if os.name != "nt":
        raise RuntimeError(
            "En Mac interrumpe el comando export con Ctrl+C; solo se detiene su proceso hijo."
        )
    query = "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor-Cmd.exe'\" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", query],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    items = json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(items, dict):
        items = [items]
    count = 0
    script_paths = [
        str(ROOT / "scripts" / name).replace("\\", "/").lower()
        for name in (
            "export_nexo_web.py",
            "export_nexo_native_face.py",
            "export_lira_web.py",
            "export_elian_web.py",
            "export_family_web.py",
        )
    ]
    from avatar_web_storage import runtime_root

    log_paths = [
        str(p).replace("\\", "/").lower()
        for p in (ROOT / "data/local-avatar/web-export", runtime_root() / "web-export")
    ]
    for item in items:
        command = (item.get("CommandLine") or "").replace("\\", "/").lower()
        if (
            any(p in command for p in script_paths)
            and any(p in command for p in log_paths)
            and "-run=pythonscript" in command
        ):
            subprocess.run(
                ["taskkill", "/PID", str(int(item["ProcessId"])), "/T", "/F"],
                check=True,
            )
            count += 1
    print(
        f"Exportaciones detenidas: {count}. El editor normal y los servicios de voz no se modifican."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("export", "install", "inspect", "cancel", "storage")
    )
    parser.add_argument("--path", type=Path)
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Instalar un candidato local sin cambiar la entrega de llamadas.",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Exportar sin cambiar manifiestos o modelos publicados.",
    )
    parser.add_argument("--character", choices=CHARACTERS, default="NEXO")
    args = parser.parse_args()
    if args.preview_only and args.action != "install":
        parser.error("--preview-only solo se aplica a install")
    if args.no_install and args.action != "export":
        parser.error("--no-install solo se aplica a export")
    if args.action == "storage":
        from avatar_web_storage import configure

        configure(args.path)
    elif args.action == "cancel":
        cancel()
    elif args.action == "export":
        export(args.character, install_result=not args.no_install)
    elif args.path is None:
        parser.error("--path es obligatorio para install/inspect")
    elif args.action == "install":
        install(args.path, preview_only=args.preview_only)
    else:
        print(json.dumps(inspect_glb(args.path), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError) as exc:
        sys.exit(str(exc))
