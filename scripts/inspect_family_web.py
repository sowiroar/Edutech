"""Read saved character placement under NullRHI; never save or compile its studio."""

import json
import math
import os
from pathlib import Path

import unreal as u

character = os.environ["VIVA_WEB_CHARACTER"]
assert character in ("NOA", "NOVA", "ATLAS")
catalog = json.loads(
    (Path(__file__).resolve().parents[2] / "Avatar/avatars.json").read_text()
)
profile = next(
    a for a in catalog["avatars"] if a["id"] == character.lower() + "-design"
)
world = u.EditorLoadingAndSavingUtils.load_map(profile["map"])
assert world, "Missing retained map"
actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
blueprint = u.load_asset(profile["blueprint"])
main = next(a for a in actors if a.get_class() == blueprint.generated_class())
camera = next(a for a in actors if a.get_actor_label() == "VIVA_Presenter_Camera")
delta = camera.get_actor_location() - main.get_actor_location()


def transform(t):
    v, r, s = t.translation, t.rotation.rotator(), t.scale3d
    return {
        "location": [v.x, v.y, v.z],
        "rotation": [r.pitch, r.yaw, r.roll],
        "scale": [s.x, s.y, s.z],
    }


def component(c, mesh):
    return {
        "name": c.get_name(),
        "mesh": mesh.get_path_name() if mesh else None,
        "materials": [m.get_path_name() if m else None for m in c.get_materials()],
        "relative": transform(c.get_relative_transform()),
        "visible": c.is_visible(),
    }


report = {
    "character": character,
    "scene": profile["map"],
    "blueprint": profile["blueprint"],
    "transform": transform(main.get_actor_transform()),
    "frontYaw": -math.atan2(delta.x, delta.y),
    "components": [],
    "accessories": [],
    "saved_authoring_assets": False,
}
for c in main.get_components_by_class(u.SkeletalMeshComponent):
    item = component(c, c.get_skeletal_mesh_asset())
    idle = c.get_editor_property("animation_data").get_editor_property("anim_to_play")
    item["animation"] = idle.get_path_name() if idle else None
    report["components"].append(item)
for actor in actors:
    if actor == main or not actor.get_actor_label().upper().startswith(character + "_"):
        continue
    for c in actor.get_components_by_class(u.StaticMeshComponent):
        parent = c.get_attach_parent()
        mesh = c.get_editor_property("static_mesh")
        if not parent or parent.get_owner() != main or not mesh or not c.is_visible():
            continue
        report["accessories"].append(
            {
                **component(c, mesh),
                "label": actor.get_actor_label(),
                "parent": parent.get_name(),
                "socket": str(c.get_attach_socket_name()),
            }
        )
output = Path(os.environ["NEXO_WEB_EXPORT_DIR"])
(output / "scene-snapshot.json").write_text(json.dumps(report, indent=2))
print(f"VIVA_{character}_SCENE_SNAPSHOT_COMPLETE")
