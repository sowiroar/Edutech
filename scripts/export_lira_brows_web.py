"""Read Juan's existing eyebrow cards/atlas for the web copy; never save assets."""

import os
from pathlib import Path

import unreal as u

output = Path(os.environ["NEXO_WEB_EXPORT_DIR"])
mesh = u.load_asset(
    "/Game/UniversityVirtualAssistant/Characters/Unpacked/VIVA_Female/Grooms/Eyebrows_M_SlightArch_CardsMesh_Group0_LOD3"
)
assert mesh, "Missing Lira eyebrow cards"
options = u.GLTFExportOptions()
options.set_editor_property("bake_material_inputs", u.GLTFMaterialBakeMode.DISABLED)
options.set_editor_property("texture_image_format", u.GLTFTextureImageFormat.NONE)
options.set_editor_property("export_source_model", True)
u.GLTFExporter.export_to_gltf(mesh, str(output / "lira-brows.glb"), options, set())
texture = u.load_asset(
    "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Eyebrows/Eyebrows_M_SlightArch/Eyebrows_M_SlightArch_CardsAtlas_Attribute"
)
assert texture, "Missing original eyebrow atlas"
task = u.AssetExportTask()
task.object = texture
task.filename = str(output / "lira-brows-attribute.tga")
task.exporter = u.TextureExporterTGA()
task.automated = True
task.prompt = False
task.replace_identical = True
assert u.Exporter.run_asset_export_task(task), "Eyebrow atlas export failed"
print("LIRA_BROWS_WEB_EXPORTED")
