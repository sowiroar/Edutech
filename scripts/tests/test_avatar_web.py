import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "avatar_web", Path(__file__).parents[1] / "avatar_web.py"
)
web = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(web)


class BrowserExportTests(unittest.TestCase):
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
