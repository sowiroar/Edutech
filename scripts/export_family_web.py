"""Export retained NOA/NOVA/ATLAS scenes read-only to unreviewed web candidates."""

import json
import math
import os
from pathlib import Path

import unreal as u

character = os.environ["VIVA_WEB_CHARACTER"]
profiles = {
    "NOA": ("/Game/VIVA/Avatars/Noa/Maps/L_Noa", "BP_Noa_C"),
    "NOVA": ("/Game/VIVA/Avatars/Nova/Final/Maps/L_Nova_Final", "BP_Nova_Final_C"),
    "ATLAS": ("/Game/VIVA/Avatars/Atlas/Final/Maps/L_Atlas_Final", "BP_Atlas_Final_C"),
}
scene, blueprint = profiles[character]
slug = character.lower()
output = Path(os.environ["NEXO_WEB_EXPORT_DIR"])
output.mkdir(parents=True, exist_ok=True)
(output / "started.json").write_text(json.dumps({"stage": "loading-" + slug}))
world = u.EditorLoadingAndSavingUtils.load_map(scene)
assert world, "Saved map could not be loaded"
actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
main = next(a for a in actors if a.get_class().get_name() == blueprint)
selected = [main]
for actor in actors:
    if actor == main or not actor.get_actor_label().upper().startswith(character + "_"):
        continue
    # Export attached accessories, never the studio backdrop, lamps or decal volumes.
    if any(
        c.get_attach_parent() and c.get_attach_parent().get_owner() == main
        for c in actor.get_components_by_class(u.StaticMeshComponent)
    ):
        selected.append(actor)
report = {
    "character": character,
    "scene": scene,
    "source_author": "Familia VIVA / proyecto del equipo",
    "saved_authoring_assets": False,
    "export_profile": 3,
    "skin_roles": {},
    "actors": [],
    "background_source": "Uam-virtual.jpg (shared web background requested by user)",
    "animation_status": "saved idle exported; browser review pending",
}
camera = next(a for a in actors if a.get_actor_label() == "VIVA_Presenter_Camera")
delta = camera.get_actor_location() - main.get_actor_location()
report["frontYaw"] = -math.atan2(delta.x, delta.y)
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
face_materials = []
face_mesh = None
body = next(
    c
    for c in main.get_components_by_class(u.SkeletalMeshComponent)
    if c.get_name() == "Body"
)
idle = body.get_editor_property("animation_data").get_editor_property("anim_to_play")
assert idle, (
    "Saved body animation missing; do not substitute another character animation"
)
report["animation"] = idle.get_path_name()
for sync in main.get_components_by_class(u.LODSyncComponent):
    sync.set_component_tick_enabled(False)
    sync.deactivate()
for actor in selected:
    entry = {"label": actor.get_actor_label(), "components": []}
    for c in actor.get_components_by_class(u.SkeletalMeshComponent):
        mesh = c.get_skeletal_mesh_asset()
        if not mesh or not c.is_visible():
            continue
        role = (
            "face"
            if c.get_name() == "Face"
            else "body"
            if c.get_name() == "Body"
            else "clothing"
        )
        report["skin_roles"][mesh.get_name()] = role
        materials = list(c.get_materials())
        order = [
            editor.get_lod_material_slot(mesh, 0, i)
            for i in range(editor.get_num_sections(mesh, 0))
        ]
        entry["components"].append(
            {
                "name": c.get_name(),
                "mesh": mesh.get_path_name(),
                "role": role,
                "materials": [m.get_path_name() if m else None for m in materials],
                "lod_slots": order,
                "vertices": [
                    editor.get_num_verts(mesh, i) for i in range(c.get_num_lods())
                ],
            }
        )
        if role == "face":
            if character == "NOA":
                assert mesh.get_name() == "SK_Noa_AlternateFace", (
                    "Noa's retained facial identity is missing"
                )
            face_mesh = mesh
            face_materials = [materials[i] for i in order]
            slots = []
            for i, material_index in enumerate(order):
                slot = u.SkeletalMaterial()
                slot.set_editor_property(
                    "material_interface", materials[material_index]
                )
                slot.set_editor_property("material_slot_name", f"ELIAN_WEB_SLOT_{i}")
                slots.append(slot)
            mesh.set_editor_property("materials", slots)
            for i, material_index in enumerate(order):
                c.set_material(i, materials[material_index])
        c.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
        c.set_animation(None if role == "face" else idle)
        c.set_forced_lod(1)
        c.set_min_lod(0)
    for c in actor.get_components_by_class(u.StaticMeshComponent):
        mesh = c.get_editor_property("static_mesh")
        parent = c.get_attach_parent()
        entry["components"].append(
            {
                "name": c.get_name(),
                "mesh": mesh.get_path_name() if mesh else None,
                "materials": [
                    m.get_path_name() if m else None for m in c.get_materials()
                ],
                "parent": parent.get_name() if parent else None,
                "socket": str(c.get_attach_socket_name()),
                "relative_transform": str(c.get_relative_transform()),
            }
        )
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
bake = u.GLTFMaterialBakeSize()
bake.set_editor_property("x", 512)
bake.set_editor_property("y", 512)
options.set_editor_property("default_material_bake_size", bake)
report["face_material_sidecars"] = [m.get_path_name() for m in face_materials]
u.SystemLibrary.execute_console_command(world, "r.SkeletalMeshForceLOD 0")
(output / "export-setup.json").write_text(json.dumps(report, indent=2))
(output / "started.json").write_text(json.dumps({"stage": "exporting-" + slug}))
result = u.GLTFExporter.export_to_gltf(
    world, str(output / f"{slug}-source.glb"), options, set(selected)
)
# The source polygon groups are unnamed and resolve to the first material. Bake
# each missing material against the actual face UVs, not the default preview
# sphere (whose generated UV1 cannot be used by the face). Only its material and
# images are read by the packer. These transient changes are never saved.
for index, material in enumerate(face_materials[1:], 1):
    slots = []
    for i in range(len(face_materials)):
        slot = u.SkeletalMaterial()
        slot.set_editor_property("material_interface", material)
        slots.append(slot)
    face_mesh.set_editor_property("materials", slots)
    u.GLTFExporter.export_to_gltf(
        face_mesh, str(output / f"{slug}-face-material-{index}.glb"), options, set()
    )
report["result"] = str(result)
(output / "export.json").write_text(json.dumps(report, indent=2))
assert (output / f"{slug}-source.glb").is_file(), "No Elian GLB output"
print(f"VIVA_{character}_WEB_EXPORT_COMPLETE")
