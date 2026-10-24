"""Read original family skin texture sources and material expressions, without saving assets."""

import json
import os
from pathlib import Path

import unreal as u

output = Path(os.environ["NEXO_WEB_EXPORT_DIR"])
snapshot = json.loads((output / "scene-snapshot.json").read_text())
report = []
seen = set()
for c in snapshot["components"]:
    for path in c["materials"]:
        if not path or path in seen:
            continue
        seen.add(path)
        material = u.load_asset(path)
        if not isinstance(material, u.Material):
            continue
        record = {"material": path, "textures": [], "custom": []}
        for node in u.MaterialEditingLibrary.get_material_expressions(material):
            if (
                c["name"] == "Face"
                and isinstance(node, u.MaterialExpressionTextureSample)
                and node.texture
            ):
                texture = node.texture
                filename = texture.get_name() + ".tga"
                task = u.AssetExportTask()
                task.object = texture
                task.filename = str(output / filename)
                task.exporter = u.TextureExporterTGA()
                task.automated = True
                task.prompt = False
                task.replace_identical = True
                assert u.Exporter.run_asset_export_task(task), texture.get_path_name()
                record["textures"].append(
                    {"asset": texture.get_path_name(), "file": filename}
                )
            if isinstance(node, u.MaterialExpressionCustom):
                record["custom"].append(node.get_editor_property("code"))
        report.append(record)
(output / "skin-sources.json").write_text(json.dumps(report, indent=2))
print("VIVA_ORIGINAL_SKIN_TEXTURES_EXPORTED")
