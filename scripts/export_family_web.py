"""Export retained NOA/NOVA/ATLAS scenes read-only to unreviewed web candidates."""

import json
import os
from pathlib import Path

import unreal as u

character = os.environ["VIVA_WEB_CHARACTER"]
slug = character.lower()
output = Path(os.environ["NEXO_WEB_EXPORT_DIR"])
output.mkdir(parents=True, exist_ok=True)
snapshot = json.loads((output / "scene-snapshot.json").read_text())
assert (
    snapshot["character"] == character and snapshot["saved_authoring_assets"] is False
)
scene = snapshot["scene"]
(output / "started.json").write_text(json.dumps({"stage": "loading-" + slug}))
# The saved placement was read in a separate NullRHI process. Export only its
# visible parts in a transient world, without compiling unused studio decals.
world = u.EditorLoadingAndSavingUtils.load_map("/Engine/Maps/Entry")
aa = u.get_editor_subsystem(u.EditorActorSubsystem)


def to_transform(t):
    pitch, yaw, roll = t["rotation"]
    return u.Transform(
        location=u.Vector(*t["location"]),
        rotation=u.Rotator(pitch=pitch, yaw=yaw, roll=roll),
        scale=u.Vector(*t["scale"]),
    )


bp = u.load_asset(snapshot["blueprint"])
main = aa.spawn_actor_from_class(bp.generated_class(), u.Vector())
main.set_actor_label(character)
main.set_actor_transform(to_transform(snapshot["transform"]), False, True)
components = {
    c.get_name(): c for c in main.get_components_by_class(u.SkeletalMeshComponent)
}
for item in snapshot["components"]:
    c = components[item["name"]]
    c.set_skeletal_mesh_asset(u.load_asset(item["mesh"]) if item["mesh"] else None)
    c.set_visibility(item["visible"])
    c.set_relative_transform(to_transform(item["relative"]), False, True)
    for index, material in enumerate(item["materials"]):
        c.set_material(index, u.load_asset(material) if material else None)
selected = [main]
for item in snapshot["accessories"]:
    actor = aa.spawn_actor_from_class(u.StaticMeshActor, u.Vector())
    actor.set_actor_label(item["label"])
    c = actor.static_mesh_component
    c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_static_mesh(u.load_asset(item["mesh"]))
    for index, material in enumerate(item["materials"]):
        c.set_material(index, u.load_asset(material) if material else None)
    actor.attach_to_component(
        components[item["parent"]],
        item["socket"],
        u.AttachmentRule.SNAP_TO_TARGET,
        u.AttachmentRule.SNAP_TO_TARGET,
        u.AttachmentRule.SNAP_TO_TARGET,
        False,
    )
    c.set_relative_transform(to_transform(item["relative"]), False, True)
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
report["frontYaw"] = snapshot["frontYaw"]
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
face_materials = []
face_mesh = None
body = next(
    c
    for c in main.get_components_by_class(u.SkeletalMeshComponent)
    if c.get_name() == "Body"
)
idle_path = next(c["animation"] for c in snapshot["components"] if c["name"] == "Body")
idle = u.load_asset(idle_path) if idle_path else None
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
