"""Read-only export from authoring assets to a separate web delivery file."""

import json
import math
import os
from pathlib import Path

import unreal as u

output = Path(
    os.environ.get(
        "NEXO_WEB_EXPORT_DIR",
        str(Path(__file__).resolve().parents[1] / "data/local-avatar/web-export"),
    )
)
output.mkdir(parents=True, exist_ok=True)
(output / "started.json").write_text(
    json.dumps({"stage": "loading-map"}), encoding="utf-8"
)
scene = "/Game/VIVA/Avatars/Nexo/NativeFinal/L_Nexo_Mateo_Work"
world = u.EditorLoadingAndSavingUtils.load_map(scene)
assert world, "NEXO map could not be loaded"
actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
selected = [
    a
    for a in actors
    if a.get_actor_label() in ("NEXO_Native_Preview", "NEXO_Native_ClassicHair")
    and (
        a.get_components_by_class(u.SkeletalMeshComponent)
        or a.get_components_by_class(u.StaticMeshComponent)
    )
]
assert any(a.get_class().get_name() == "BP_NexoMateo_C" for a in selected), (
    "NEXO not present"
)
report = {
    "scene": scene,
    "actors": [],
    "saved_authoring_assets": False,
    "frontYaw": 0.0,
    "export_profile": 3,
    "animation_status": "native idle exported; browser validation pending",
}
report["nexo_scene_actors"] = [
    {
        "label": a.get_actor_label(),
        "class": a.get_class().get_name(),
        "meshes": [c.get_name() for c in a.get_components_by_class(u.MeshComponent)],
    }
    for a in actors
    if "nexo" in a.get_actor_label().lower()
]
mesh_editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
idle = u.load_asset(
    "/Game/VIVA/Avatars/Nexo/NativeFinal/Animation/AS_NexoMateo_NativeIdle"
)
assert idle, "Native idle animation is missing"
main_actor = next(a for a in selected if a.get_class().get_name() == "BP_NexoMateo_C")
face_mesh = None
custom_skin = None
for sync in main_actor.get_components_by_class(u.LODSyncComponent):
    sync.set_component_tick_enabled(False)
    sync.deactivate()
camera = next(
    (a for a in actors if a.get_actor_label() == "VIVA_Presenter_Camera"), None
)
if camera:
    delta = camera.get_actor_location() - main_actor.get_actor_location()
    report["frontYaw"] = -math.atan2(delta.x, delta.y)
for actor in selected:
    entry = {"label": actor.get_actor_label(), "components": []}
    for c in actor.get_components_by_class(u.SkeletalMeshComponent):
        mesh = c.get_editor_property("skeletal_mesh")
        if mesh:
            component_report = {"name": c.get_name(), "mesh": mesh.get_path_name()}
            entry["components"].append(component_report)
            if "FaceMesh" in mesh.get_name():
                face_mesh = mesh
                # This MetaHuman has an unnamed head polygon group that the exporter
                # resolves to the wrong imported slot (teeth). Fresh export-only
                # slots omit imported names so the parser uses polygon-group IDs.
                materials = list(c.get_materials())
                slots = [
                    mesh_editor.get_lod_material_slot(mesh, 0, i)
                    for i in range(mesh_editor.get_num_sections(mesh, 0))
                ]
                component_report["lod_material_slots"] = slots
                component_report["materials_before"] = [
                    m.get_path_name() if m else None for m in materials
                ]
                assert materials, "Face component was reconstructed during export setup"
                assert len(materials) == 4, "Unexpected face material layout"
                export_materials = [
                    materials[3],
                    materials[0],
                    materials[2],
                    materials[1],
                ]
                custom_skin = materials[3]
                # Retain Mateo's own baked skin, including its normal/roughness
                # maps. The former flat stylized material discarded those maps.
                # Procedural cyan traces are added by the browser shader.
                native_skin = u.load_asset(
                    "/Game/VIVA/Avatars/Nexo/NativeFinal/Assembled/NexoMateo/Face/Materials/MI_Face_Skin_Baked_LOD5to7_VT"
                )
                assert native_skin, "Original Mateo skin material is missing"
                export_materials[0] = native_skin
                report["face_finish"] = (
                    "native Mateo skin maps; browser surface refinement and cyan traces"
                )
                export_slots = []
                for index, material in enumerate(export_materials):
                    slot = u.SkeletalMaterial()
                    slot.set_editor_property("material_interface", material)
                    slot.set_editor_property(
                        "material_slot_name", f"NEXO_WEB_SLOT_{index}"
                    )
                    export_slots.append(slot)
                # Process-local only. No save/checkout operation is performed on this asset.
                mesh.set_editor_property("materials", export_slots)
                for index, material in enumerate(export_materials):
                    c.set_material(index, material)
                component_report["export_materials"] = [
                    m.get_path_name() for m in export_materials
                ]
        # Only transient component state changes. Retain native idle for body and clothing.
        c.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
        c.set_animation(idle if mesh and "FaceMesh" not in mesh.get_name() else None)
        # Use runtime setters: set_editor_property reruns BP construction and invalidates Face/Clothing.
        # Component LOD is one-based. Also reset the component minimum and force
        # global LOD 0 below, so bake ticks cannot reapply the cinematic preview LOD.
        c.set_forced_lod(1)
        # UE 5.8 exposes bOverrideMinLod as override_min_lod, hiding the method
        # with that Python name. The legacy callable still sets MinLodModel.
        c.set_min_lod(0)
    report["actors"].append(entry)
options = u.GLTFExportOptions()
for name, value in {
    "export_source_model": True,
    "default_level_of_detail": 0,
    "export_vertex_skin_weights": True,
    "export_morph_targets": True,
    "export_animation_sequences": True,
    "export_level_sequences": False,
    "export_hidden_in_game": False,
    "export_cameras": False,
    "export_lights": False,
    "export_vertex_colors": False,
    "use_mesh_quantization": True,
    "texture_image_quality": 80,
}.items():
    options.set_editor_property(name, value)
options.set_editor_property("texture_image_format", u.GLTFTextureImageFormat.JPEG)
bake_size = u.GLTFMaterialBakeSize()
bake_size.set_editor_property("x", 512)
bake_size.set_editor_property("y", 512)
options.set_editor_property("default_material_bake_size", bake_size)
# Material baking ticks the world. Prevent MetaHuman's cinematic LODSync from
# putting the face back at its last preview LOD while the export runs.
u.SystemLibrary.execute_console_command(world, "r.SkeletalMeshForceLOD 0")
report["lod_diagnostics"] = [
    {
        "name": c.get_name(),
        "forced_lod_1_based": c.get_forced_lod(),
        "lod_count": c.get_num_lods(),
        "vertices_per_lod": [
            mesh_editor.get_num_verts(c.get_skeletal_mesh_asset(), i)
            for i in range(c.get_num_lods())
        ],
    }
    for c in main_actor.get_components_by_class(u.SkeletalMeshComponent)
]
(output / "export-setup.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
(output / "started.json").write_text(
    json.dumps({"stage": "exporting-glb"}), encoding="utf-8"
)
result = u.GLTFExporter.export_to_gltf(
    world, str(output / "nexo-source.glb"), options, set(selected)
)
# Keep the approved albedo/brows/lips, while retaining the native normal map.
# The native skin's glTF albedo alone bakes subsurface shadows too dark around
# the eyes. Bake the saved stylized material on the same face as a color sidecar.
slots = []
for i in range(4):
    slot = u.SkeletalMaterial()
    slot.set_editor_property("material_interface", custom_skin)
    slots.append(slot)
face_mesh.set_editor_property("materials", slots)
u.GLTFExporter.export_to_gltf(
    face_mesh, str(output / "nexo-original-color.glb"), options, set()
)
report["face_color_source"] = custom_skin.get_path_name()
report["result"] = str(result)
(output / "export.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
assert (output / "nexo-source.glb").is_file(), "No GLB output"
print("VIVA_WEB_EXPORT_COMPLETE")
