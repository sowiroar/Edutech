import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from native_nexo_face_glb import replace_native_face
from optimize_nexo_glb import GLB


class NativeFaceTests(unittest.TestCase):
    def fixture(self):
        g = object.__new__(GLB)
        g.binary = bytearray()
        g.doc = {
            "asset": {"version": "2.0"},
            "accessors": [],
            "bufferViews": [],
            "meshes": [{"name": "Face", "primitives": []}],
            "nodes": [{"name": "a"}, {"name": "b"}, {"mesh": 0, "skin": 0}],
            "skins": [{"name": "SKM_CH_Nexo_MateoNative_FaceMesh", "joints": [0, 1]}],
        }
        positions = [(0.0, 0.0, 0.0), (0.01, 0.0, 0.0), (0.0, 0.01, 0.0)]
        for material, count in enumerate((5048, 796, 216, 216)):
            attrs = {
                "POSITION": g.append(positions, "VEC3", 5126),
                "NORMAL": g.append([(0.0, 0.0, 1.0)] * 3, "VEC3", 5126),
                "TEXCOORD_0": g.append(
                    [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)], "VEC2", 5126
                ),
                "JOINTS_0": g.append([(0, 1, 0, 0)] * 3, "VEC4", 5123),
                "WEIGHTS_0": g.append([(0.75, 0.25, 0.0, 0.0)] * 3, "VEC4", 5126),
            }
            g.doc["meshes"][0]["primitives"].append(
                {
                    "attributes": attrs,
                    "material": material,
                    "indices": g.append(
                        [(i,) for i in [0, 1, 2] * count], "SCALAR", 5123
                    ),
                }
            )
        native = copy.deepcopy(g)
        native.doc["skins"][0]["joints"] = [1, 0]
        for p in native.doc["meshes"][0]["primitives"]:
            for key in ("POSITION", "NORMAL"):
                p["attributes"][key] = native.append(
                    [(x, z, y) for x, y, z in native.read(p["attributes"][key])],
                    "VEC3",
                    5126,
                )
            p["attributes"]["JOINTS_0"] = native.append(
                [(1, 0, 0, 0)] * 3, "VEC4", 5123
            )
        return g, native

    def test_converts_coordinates_remaps_joints_and_preserves_original_rig(self):
        g, native = self.fixture()
        nodes, skins = copy.deepcopy(g.doc["nodes"]), copy.deepcopy(g.doc["skins"])
        expected = copy.deepcopy(g)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.glb"
            native.write(path)
            result = replace_native_face(g, path)
        self.assertEqual(g.doc["nodes"], nodes)
        self.assertEqual(g.doc["skins"], skins)
        for a, b in zip(
            g.doc["meshes"][0]["primitives"], expected.doc["meshes"][0]["primitives"]
        ):
            for key in b["attributes"]:
                if key != "JOINTS_0":
                    self.assertEqual(
                        g.read(a["attributes"][key]),
                        expected.read(b["attributes"][key]),
                    )
            for joints, weights in zip(
                g.read(a["attributes"]["JOINTS_0"]),
                g.read(a["attributes"]["WEIGHTS_0"]),
            ):
                self.assertEqual(
                    {j: w for j, w in zip(joints, weights) if w}, {0: 0.75, 1: 0.25}
                )
            self.assertEqual(g.read(a["indices"]), expected.read(b["indices"]))
            self.assertEqual(a["material"], b["material"])
        self.assertTrue(result["retained_original_skeleton"])

    def test_rejects_a_different_character_or_displaced_face(self):
        g, native = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.glb"
            native.write(path)
            wrong = copy.deepcopy(g)
            wrong.doc["skins"][0]["name"] = "OtherCharacter"
            with self.assertRaisesRegex(ValueError, "original Mateo"):
                replace_native_face(wrong, path)
            attrs = native.doc["meshes"][0]["primitives"][0]["attributes"]
            attrs["POSITION"] = native.append(
                [(x + 1, y, z) for x, y, z in native.read(attrs["POSITION"])],
                "VEC3",
                5126,
            )
            native.write(path)
            with self.assertRaisesRegex(ValueError, "bounds differ"):
                replace_native_face(g, path)


if __name__ == "__main__":
    unittest.main()
