"""Read-only original Mateo head DNA to transient LOD3 geometry.

Run in a separate NullRHI commandlet; never saves authoring packages.
The assembled rig remains authoritative in native_nexo_face_glb.py.
"""

import json
import os
import shutil
from pathlib import Path

import unreal as u

output = Path(os.environ["NEXO_WEB_EXPORT_DIR"])
character = u.load_asset("/Game/VIVA/Avatars/Nexo/NativeFinal/CH_Nexo_MateoNative")
assert character, "Original Mateo character is missing"
params = u.MetaHumanDNAExportParams()
params.set_editor_property("project_path", "")
params.set_editor_property("external_path", str(output))
params.set_editor_property("dna_head", True)
params.set_editor_property("dna_body", False)
u.MetaHumanCharacterExportBlueprintLibrary.export_dna(character, params)
dna = output / "CH_Nexo_MateoNative_Head.dna"
assert dna.is_file() and dna.stat().st_size > 1000000, "Full head DNA was not exported"
source_file = dna.with_suffix(".mhdna")
shutil.copyfile(dna, source_file)
source = u.InterchangeManager.create_source_data(str(source_file))
holder_class = u.load_class(None, "/Script/RigLogicModule.DNAConfigHolder")
assert holder_class, "DNA import support is unavailable"
# Default translator geometry uses Z-up. The merger validates and converts it.
holder = u.new_object(holder_class, outer=source)
source.set_context_object_by_tag("DNAConfig", holder)
pipeline = u.load_asset("/MetaHumanSDK/DefaultDNAPipeline")
pipeline.get_editor_property("mesh_pipeline").set_editor_property(
    "import_morph_targets", False
)
pipeline.get_editor_property(
    "common_skeletal_meshes_and_animations_properties"
).set_editor_property("skeleton", None)
params = u.ImportAssetParameters()
params.set_editor_property("is_automated", True)
params.set_editor_property("replace_existing", False)
params.set_editor_property("destination_name", "NexoNativeFaceWeb")
params.set_editor_property(
    "override_pipelines", [u.SoftObjectPath(pipeline.get_path_name())]
)
u.InterchangeManager.get_interchange_manager_scripted().import_asset(
    "/Engine/Transient/NexoFaceWeb", source, params
)
meshes = [
    obj
    for obj in u.ObjectIterator(u.SkeletalMesh)
    if "NexoFaceWeb" in obj.get_path_name()
]
assert len(meshes) == 1, "Expected one transient native face"
mesh = meshes[0]
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
options = u.GLTFExportOptions()
options.set_editor_property("export_source_model", True)
options.set_editor_property("default_level_of_detail", 3)
options.set_editor_property("export_vertex_skin_weights", True)
options.set_editor_property("export_morph_targets", False)
options.set_editor_property("bake_material_inputs", u.GLTFMaterialBakeMode.DISABLED)
options.set_editor_property("texture_image_format", u.GLTFTextureImageFormat.NONE)
target = output / "nexo-native-lod3.glb"
u.GLTFExporter.export_to_gltf(mesh, str(target), options, set())
assert target.is_file(), "Native face GLB export failed"
report = {
    "source": character.get_path_name(),
    "saved_authoring_assets": False,
    "lod": 3,
    "bytes": target.stat().st_size,
    "lod_vertices": [
        editor.get_num_verts(mesh, i) for i in range(editor.get_lod_count(mesh))
    ],
}
(output / "native-face.json").write_text(json.dumps(report, indent=2), encoding="utf8")
print("NEXO_NATIVE_FACE_COMPLETE")
