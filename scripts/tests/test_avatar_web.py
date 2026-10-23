import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "avatar_web", Path(__file__).parents[1] / "avatar_web.py"
)
web = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(web)


class BrowserExportTests(unittest.TestCase):
    def test_preview_install_preserves_production_manifest_and_background(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, out = root / "Edutech", root / "export"
            out.mkdir()
            (root / "Avatar").mkdir()
            (root / "Avatar/Uam-virtual.jpg").write_bytes(b"candidate background")
            public = repo / "agent-starter-react/public/avatars/elian"
            public.mkdir(parents=True)
            (public / "manifest.json").write_text('{"production":true}')
            (public / "uam-background.jpg").write_bytes(b"production background")
            source = self.fixture(out)
            source.rename(out / "elian-source.glb")
            for i in (1, 2, 3):
                (out / f"elian-face-material-{i}.glb").write_bytes(b"sidecar")
            (out / "export.json").write_text(
                json.dumps(
                    {
                        "character": "ELIAN",
                        "export_profile": 3,
                        "saved_authoring_assets": False,
                        "frontYaw": 0,
                    }
                )
            )

            def optimize(source, target, **_):
                target.write_bytes(source.read_bytes())
                return {"has_mouth_rig": True}

            with (
                patch.object(web, "ROOT", repo),
                patch.dict(
                    web.sys.modules,
                    {
                        "optimize_nexo_glb": SimpleNamespace(optimize=optimize),
                    },
                ),
            ):
                web.install(out, preview_only=True)
            self.assertEqual(
                (public / "manifest.json").read_text(), '{"production":true}'
            )
            self.assertEqual(
                (public / "uam-background.jpg").read_bytes(), b"production background"
            )
            candidate = json.loads((public / "manifest.preview.json").read_text())
            self.assertEqual(candidate["visual_review"], "pending")
            self.assertEqual(
                (public / "uam-background.preview.jpg").read_bytes(),
                b"candidate background",
            )

    def test_report_does_not_make_a_partial_export_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "export.json").write_text("{}")
            (root / "lira-source.glb").write_bytes(b"partial")
            with self.assertRaisesRegex(ValueError, "lira-brows"):
                web.validate_export_files(root, "LIRA")

    def test_nexo_cannot_silently_fall_back_to_the_rejected_face(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("export.json", "nexo-source.glb", "nexo-original-color.glb"):
                (root / name).write_bytes(b"fixture")
            web.validate_export_files(root, "NEXO", require_native_face=False)
            with self.assertRaisesRegex(ValueError, "nexo-native-lod3"):
                web.validate_export_files(root, "NEXO")
            for name in ("nexo-native-lod3.glb", "native-face.json"):
                (root / name).write_bytes(b"fixture")
            web.validate_export_files(root, "NEXO")

    def test_mac_editor_and_process_group_do_not_use_windows_flags(self):
        with (
            patch.dict(web.os.environ, {}, clear=True),
            patch.object(web.sys, "platform", "darwin"),
        ):
            self.assertEqual(web.editor_path().name, "UnrealEditor-Cmd")
        with patch.object(web.os, "name", "posix"):
            self.assertEqual(web.process_options(), {"start_new_session": True})

    def test_unreal_override_can_select_a_different_installation(self):
        with patch.dict(
            web.os.environ, {"UNREAL_EDITOR_CMD": "/custom/UnrealEditor-Cmd"}
        ):
            self.assertEqual(str(web.editor_path()), "/custom/UnrealEditor-Cmd")

    def test_timeout_only_stops_owned_process_group(self):
        child = Mock(pid=12345)
        child.poll.return_value = None
        with (
            patch.object(web.os, "name", "posix"),
            patch.object(web.os, "killpg", create=True) as kill,
        ):
            web.stop_export(child)
        kill.assert_called_once_with(child.pid, web.signal.SIGTERM)
        child.wait.assert_called_once_with(timeout=10)

    def test_failure_explains_python_error_without_dumping_whole_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "console.log").write_text(
                "unrelated log details\n"
                "[0]LogPython: Error: TypeError: 'bool' object is not callable\n",
                encoding="utf-8",
            )
            message = web.export_failure(root, 4294967295)
            self.assertIn("TypeError: 'bool' object is not callable", message)
            self.assertNotIn("unrelated log details", message)

    def fixture(self, directory, **overrides):
        doc = {
            "asset": {"version": "2.0"},
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
            "accessors": [{"count": 8}, {"count": 36}],
            "skins": [{"joints": [0]}],
        }
        doc.update(overrides)
        payload = json.dumps(doc).encode()
        payload += b" " * ((-len(payload)) % 4)
        data = (
            struct.pack(
                "<4sIIII", b"glTF", 2, 20 + len(payload), len(payload), 0x4E4F534A
            )
            + payload
        )
        path = Path(directory) / "fixture.glb"
        path.write_bytes(data)
        return path

    def test_counts_visible_instances_not_unique_meshes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory, nodes=[{"mesh": 0}, {"mesh": 0}])
            self.assertEqual(web.inspect_glb(path)["triangles"], 24)

    def test_no_external_textures_or_unbound_static_body(self):
        with tempfile.TemporaryDirectory() as directory:
            for overrides in (
                {"images": [{"uri": "https://external/image.png"}]},
                {"skins": []},
            ):
                with self.assertRaises(ValueError):
                    web.inspect_glb(self.fixture(directory, **overrides))

    def test_rejects_truncated_and_over_budget_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory)
            path.write_bytes(path.read_bytes()[:-3])
            with self.assertRaises(ValueError):
                web.inspect_glb(path)
            path = self.fixture(directory, accessors=[{"count": 8}, {"count": 600_000}])
            with self.assertRaises(ValueError):
                web.inspect_glb(path)


if __name__ == "__main__":
    unittest.main()
