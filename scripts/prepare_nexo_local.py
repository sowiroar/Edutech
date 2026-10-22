"""Executed by Unreal only in the disposable Windows build copy, never in authoring."""

import json
import os
from pathlib import Path

import unreal as u

project = Path(u.Paths.project_dir()).resolve()
expected = Path(os.environ["VIVA_BUILD_PROJECT"]).resolve()
assert project == expected and (project / ".viva-local-build").is_file(), (
    "Refusing to edit authoring project"
)
catalog = json.loads((project / "avatars.json").read_text(encoding="utf-8"))
entry = next(e for e in catalog["avatars"] if e["id"] == "nexo-design")
bp = u.load_asset(entry["blueprint"])
assert bp
sub = u.get_engine_subsystem(u.SubobjectDataSubsystem)
fn = u.SubobjectDataBlueprintFunctionLibrary
parts = [
    (h, fn.get_object_for_blueprint(fn.get_data(h), bp))
    for h in sub.k2_gather_subobject_data_for_blueprint(bp)
]
cls = u.load_class(None, "/Script/VivaAvatar.VivaAvatarReceiver")
assert cls
receivers = list(
    {c.get_path_name(): c for _, c in parts if c and c.get_class() == cls}.values()
)
assert len(receivers) <= 1
if not receivers:
    parent = next(h for h, c in parts if c and isinstance(c, u.SceneComponent))
    handle, reason = sub.add_new_subobject(
        u.AddNewSubobjectParams(
            parent_handle=parent, new_class=cls, blueprint_context=bp
        )
    )
    assert not str(reason), str(reason)
    sub.rename_subobject(handle, "VivaVoiceReceiver")
    receivers = [fn.get_object_for_blueprint(fn.get_data(handle), bp)]
receiver = receivers[0]
receiver.set_editor_property("bridge_url", "ws://127.0.0.1:8766")
receiver.set_editor_property("enable_speech_animation", True)
receiver.set_editor_property("live_link_subject", "VivaNexo")
u.BlueprintEditorLibrary.compile_blueprint(bp)
assert u.EditorAssetLibrary.save_loaded_asset(bp)
world = u.EditorLoadingAndSavingUtils.load_map(entry["map"])
assert world
actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
cameras = [a for a in actors if isinstance(a, u.CameraActor)]
preferred = [
    a
    for a in cameras
    if a.get_actor_label() in ("VIVA_Presenter_Camera", "UA_Presenter_Camera")
]
assert len(preferred) == 1 or len(cameras) == 1, (
    "Camera ambiguous; inspect before packaging"
)
camera = preferred[0] if len(preferred) == 1 else cameras[0]
for c in cameras:
    c.set_editor_property(
        "auto_activate_for_player",
        u.AutoReceiveInput.PLAYER0 if c == camera else u.AutoReceiveInput.DISABLED,
    )
world.get_world_settings().set_editor_property(
    "default_game_mode",
    u.load_class(None, "/Script/VivaAvatar.VivaPresentationGameMode"),
)
characters = [
    a
    for a in actors
    if a.get_class().get_path_name() == entry["blueprint"] + "." + bp.get_name() + "_C"
]
assert len(characters) == 1, "Expected one NEXO actor"
characters[0].set_editor_property(
    "tags",
    list(dict.fromkeys([*characters[0].get_editor_property("tags"), u.Name("NEXO")])),
)
assert len(characters[0].get_components_by_class(cls)) == 1
assert u.EditorLoadingAndSavingUtils.save_map(world, entry["map"])
(project / "prepared.json").write_text(
    json.dumps(
        {
            "map": entry["map"],
            "blueprint": entry["blueprint"],
            "camera": camera.get_actor_label(),
            "design": "nexo-design",
            "voice_ready": False,
            "validation": "receiver configured; runtime speech and visual validation pending",
        }
    ),
    encoding="utf-8",
)
