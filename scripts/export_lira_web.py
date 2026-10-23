"""Export Juan's retained Lira to the web, without saving authoring assets."""

import json
import os
from pathlib import Path

import unreal as u

output = Path(os.environ["NEXO_WEB_EXPORT_DIR"])
output.mkdir(parents=True, exist_ok=True)
(output / "started.json").write_text(json.dumps({"stage": "loading-lira"}))
# Fail before the expensive material bake when the optional Epic content is absent.
assert u.load_asset(
    "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Eyebrows/Eyebrows_M_SlightArch/Eyebrows_M_SlightArch_CardsAtlas_Attribute"
), (
    "Falta el atlas SlightArch original: instalar MetaHuman Creator Core Data desde las opciones de Unreal en Epic Games Launcher."
)
scene = "/Game/VIVA/Avatars/Lira/Maps/L_Lira"
# Export retained assets in an unsaved world. Loading the studio also compiles
# its deferred FaceTraces projector, which is not supported by glTF and can
# keep DXC optimizing for many minutes. Original map/materials are untouched.
world = u.EditorLoadingAndSavingUtils.load_map("/Engine/Maps/Entry")
assert world, "Export world could not be loaded"
aa = u.get_editor_subsystem(u.EditorActorSubsystem)
bp = u.load_asset("/Game/VIVA/Avatars/Lira/Blueprints/BP_Lira")
main_actor = aa.spawn_actor_from_class(
    bp.generated_class(), u.Vector(), u.Rotator(yaw=90)
)
main_actor.set_actor_label("LIRA")
selected = [main_actor]
parts = {
    c.get_name(): c for c in main_actor.get_components_by_class(u.SkeletalMeshComponent)
}
for label, mesh_path, material_path, parent, bone in [
    (
        "LIRA_HairCards",
        "/Game/VIVA/Avatars/Lira/Meshes/SM_Lira_HairCardsBone",
        "/Game/VIVA/Avatars/Lira/Materials/MI_Lira_HairCards",
        "Face",
        "head",
    ),
    (
        "LIRA_Collar",
        "/Game/VIVA/Avatars/Lira/Meshes/SM_Lira_SoftCollarBone_v5",
        "/Game/VIVA/Avatars/Lira/Materials/M_Lira_CollarFabric",
        "Body",
        "neck_01",
    ),
]:
    actor = aa.spawn_actor_from_class(u.StaticMeshActor, u.Vector())
    actor.set_actor_label(label)
    c = actor.static_mesh_component
    c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_static_mesh(u.load_asset(mesh_path))
    for index in range(c.get_num_materials()):
        c.set_material(index, u.load_asset(material_path))
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    actor.attach_to_component(
        parts[parent],
        bone,
        u.AttachmentRule.SNAP_TO_TARGET,
        u.AttachmentRule.SNAP_TO_TARGET,
        u.AttachmentRule.SNAP_TO_TARGET,
        False,
    )
    selected.append(actor)
report = {
    "character": "LIRA",
    "source_author": "JuanGonzalezx",
    "scene": scene,
    "actors": [],
    "saved_authoring_assets": False,
    "frontYaw": 1.7850026767815772,
    "export_world": "/Engine/Maps/Entry",
    "export_profile": 3,
    "skin_roles": {},
    "animation_status": "exported idle; browser validation pending",
}
mesh_editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
for sync in main_actor.get_components_by_class(u.LODSyncComponent):
    sync.set_component_tick_enabled(False)
    sync.deactivate()
body = next(
    c
    for c in main_actor.get_components_by_class(u.SkeletalMeshComponent)
    if c.get_name() == "Body"
)
idle = body.get_editor_property("animation_data").get_editor_property("anim_to_play")
if not idle:
    idle = u.load_asset(
        "/Game/UniversityVirtualAssistant/NEXO_Stylized/Animation/AS_NEXO_PresenterHands"
    )
assert idle, "Missing saved presentation animation"
report["animation"] = idle.get_path_name()
for actor in selected:
    entry = {"label": actor.get_actor_label(), "components": []}
    for c in actor.get_components_by_class(u.SkeletalMeshComponent):
        mesh = c.get_skeletal_mesh_asset()
        if not mesh:
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
        entry["components"].append(
            {
                "name": c.get_name(),
                "mesh": mesh.get_path_name(),
                "role": role,
                "materials": [m.get_path_name() if m else None for m in materials],
                "lod_slots": [
                    mesh_editor.get_lod_material_slot(mesh, 0, i)
                    for i in range(mesh_editor.get_num_sections(mesh, 0))
                ],
                "vertices": [
                    mesh_editor.get_num_verts(mesh, i) for i in range(c.get_num_lods())
                ],
            }
        )
        if role == "face":
            # Source polygon groups use LOD section order, whereas imported slots
            # put skin at index 6. Give the exporter unambiguous transient slots.
            order = [
                mesh_editor.get_lod_material_slot(mesh, 0, i)
                for i in range(mesh_editor.get_num_sections(mesh, 0))
            ]
            export_slots = []
            for index, material_index in enumerate(order):
                slot = u.SkeletalMaterial()
                slot.set_editor_property(
                    "material_interface", materials[material_index]
                )
                slot.set_editor_property("material_slot_name", f"LIRA_WEB_SLOT_{index}")
                export_slots.append(slot)
            mesh.set_editor_property("materials", export_slots)
            for index, material_index in enumerate(order):
                c.set_material(index, materials[material_index])
            entry["components"][-1]["export_material_order"] = order
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
                "attach_parent": parent.get_name() if parent else None,
                "socket": str(c.get_attach_socket_name()),
                "transform": str(actor.get_actor_transform()),
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
u.SystemLibrary.execute_console_command(world, "r.SkeletalMeshForceLOD 0")
(output / "export-setup.json").write_text(json.dumps(report, indent=2))
(output / "started.json").write_text(json.dumps({"stage": "exporting-lira"}))
result = u.GLTFExporter.export_to_gltf(
    world, str(output / "lira-source.glb"), options, set(selected)
)
report["result"] = str(result)
(output / "export.json").write_text(json.dumps(report, indent=2))
assert (output / "lira-source.glb").is_file(), "No Lira GLB output"
exec(
    compile(
        (Path(__file__).parent / "export_lira_brows_web.py").read_text(),
        "export_lira_brows_web.py",
        "exec",
    )
)
print("VIVA_LIRA_WEB_EXPORT_COMPLETE")
