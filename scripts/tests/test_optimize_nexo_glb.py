import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "optimize_nexo_glb", Path(__file__).parents[1] / "optimize_nexo_glb.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class OptimizeTests(unittest.TestCase):
    def fixture(self, path):
        g = object.__new__(module.GLB)
        g.binary = bytearray()
        g.doc = {
            "asset": {"version": "2.0"},
            "scenes": [{"nodes": [0, 6]}],
            "scene": 0,
            "nodes": [{"name": "root", "children": [1, 2, 3, 4, 5, 7]}]
            + [{"name": f"joint{i}"} for i in range(1, 6)]
            + [{"name": "Body", "mesh": 0, "skin": 0}, {"name": "unused"}],
            "accessors": [],
            "bufferViews": [],
            "meshes": [],
            "skins": [],
            "materials": [],
        }
        pos = g.append(
            [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], "VEC3", 5126
        )
        idx = g.append([(0,), (1,), (2,)], "SCALAR", 5123)
        j0 = g.append([(1, 2, 3, 4)] * 3, "VEC4", 5123)
        w0 = g.append([(0.3, 0.3, 0.2, 0.1)] * 3, "VEC4", 5126)
        j1 = g.append([(5, 0, 0, 0)] * 3, "VEC4", 5123)
        w1 = g.append([(0.1, 0.0, 0.0, 0.0)] * 3, "VEC4", 5126)
        ibm = g.append(
            [
                (
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                )
            ]
            * 6,
            "MAT4",
            5126,
        )
        g.doc["meshes"] = [
            {
                "name": "Body",
                "primitives": [
                    {
                        "indices": idx,
                        "attributes": {
                            "POSITION": pos,
                            "JOINTS_0": j0,
                            "WEIGHTS_0": w0,
                            "JOINTS_1": j1,
                            "WEIGHTS_1": w1,
                        },
                    }
                ],
            }
        ]
        g.doc["skins"] = [
            {"name": "BodyMesh", "joints": list(range(6)), "inverseBindMatrices": ibm}
        ]
        times = g.append([(0.0,), (1.0,)], "SCALAR", 5126)
        rotations = g.append(
            [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.1, 0.995)], "VEC4", 5126
        )
        g.doc["animations"] = [
            {
                "name": "idle",
                "samplers": [{"input": times, "output": rotations}],
                "channels": [{"sampler": 0, "target": {"node": 1, "path": "rotation"}}],
            }
        ]
        g.write(path)

    def test_preserves_geometry_and_animation_while_remapping_skin(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "source.glb", Path(temp) / "web.glb"
            self.fixture(source)
            before = module.GLB(source)
            report = module.optimize(source, target)
            after = module.GLB(target)
            p0 = before.doc["meshes"][0]["primitives"][0]
            p1 = after.doc["meshes"][0]["primitives"][0]
            self.assertEqual(
                before.read(p0["attributes"]["POSITION"]),
                after.read(p1["attributes"]["POSITION"]),
            )
            self.assertEqual(before.read(p0["indices"]), after.read(p1["indices"]))
            self.assertEqual(report["skins_after"], 4)
            self.assertLess(report["nodes_after"], report["nodes_before"])
            self.assertNotIn("WEIGHTS_1", p1["attributes"])
            for row in after.read(p1["attributes"]["WEIGHTS_0"]):
                self.assertAlmostEqual(sum(row), 1.0, places=6)
            for row in after.read(p1["attributes"]["JOINTS_0"]):
                self.assertLess(max(row), 4)
            channel = after.doc["animations"][0]["channels"][0]
            self.assertEqual(
                after.doc["nodes"][channel["target"]["node"]]["name"], "joint1"
            )
            for accessor in after.doc["accessors"]:
                view = after.doc["bufferViews"][accessor["bufferView"]]
                self.assertLessEqual(
                    view["byteOffset"] + view["byteLength"], len(after.binary)
                )

    def test_clothing_follows_matching_body_bones(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "source.glb", Path(temp) / "web.glb"
            self.fixture(source)
            g = module.GLB(source)
            d = g.doc
            start = len(d["nodes"])
            d["nodes"].append(
                {"name": "root", "children": list(range(start + 1, start + 6))}
            )
            d["nodes"].extend({"name": f"joint{i}"} for i in range(1, 6))
            d["nodes"].append({"name": "Jacket", "mesh": 1, "skin": 1})
            d["scenes"][0]["nodes"].extend([start, start + 6])
            d["meshes"].append(copy.deepcopy(d["meshes"][0]))
            d["skins"].append(
                {
                    "name": "JacketMesh",
                    "joints": list(range(start, start + 6)),
                    "inverseBindMatrices": d["skins"][0]["inverseBindMatrices"],
                }
            )
            g.write(source)
            report = module.optimize(source, target)
            self.assertEqual(report["clothing_animation_channels_copied"], 1)
            after = module.GLB(target)
            channels = after.doc["animations"][0]["channels"]
            animated_roles = {
                after.doc["nodes"][c["target"]["node"]]["extras"]["vivaSkin"]
                for c in channels
            }
            self.assertEqual(animated_roles, {"body", "clothing"})

    def test_face_follows_body_pose_even_with_different_reference_offsets(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "source.glb", Path(temp) / "web.glb"
            self.fixture(source)
            g = module.GLB(source)
            d = g.doc
            start = len(d["nodes"])
            d["nodes"].append(
                {"name": "root", "children": list(range(start + 1, start + 6))}
            )
            d["nodes"].extend(
                {"name": f"joint{i}", "translation": [0, 0.8, 0]} for i in range(1, 6)
            )
            d["nodes"].append({"name": "Face", "mesh": 1, "skin": 1})
            d["scenes"][0]["nodes"].extend([start, start + 6])
            d["meshes"].append(copy.deepcopy(d["meshes"][0]))
            d["skins"].append(
                {
                    "name": "FaceMesh",
                    "joints": list(range(start, start + 6)),
                    "inverseBindMatrices": d["skins"][0]["inverseBindMatrices"],
                }
            )
            animation = d["animations"][0]
            animation["channels"][0]["target"]["path"] = "translation"
            output = g.append([(0.0, 1.0, 0.0), (0.0, 1.1, 0.0)], "VEC3", 5126)
            animation["samplers"][0]["output"] = output
            g.write(source)
            report = module.optimize(source, target)
            self.assertEqual(report["face_animation_channels_copied"], 1)
            after = module.GLB(target)
            animation = after.doc["animations"][0]
            self.assertEqual(len(animation["channels"]), 2)
            for channel in animation["channels"]:
                values = after.read(animation["samplers"][channel["sampler"]]["output"])
                self.assertAlmostEqual(values[0][1], 1.0)
                self.assertAlmostEqual(values[1][1], 1.1)

    def test_explicit_roles_support_juan_lira_mesh_names(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "source.glb", Path(temp) / "web.glb"
            self.fixture(source)
            g = module.GLB(source)
            g.doc["skins"][0]["name"] = "SK_Lira_Body"
            g.write(source)
            module.optimize(source, target, skin_roles={"SK_Lira_Body": "body"})
            result = module.GLB(target)
            bones = [
                n for n in result.doc["nodes"] if "vivaSkin" in n.get("extras", {})
            ]
            self.assertTrue(bones)
            self.assertEqual({n["extras"]["vivaSkin"] for n in bones}, {"body"})

    def test_exact_vertex_compaction_preserves_uv_seams_and_triangle_values(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "source.glb", Path(temp) / "web.glb"
            self.fixture(source)
            g = module.GLB(source)
            p = g.doc["meshes"][0]["primitives"][0]
            for name, index in list(p["attributes"].items()):
                a = g.doc["accessors"][index]
                rows = g.read(index, normalize=False)
                p["attributes"][name] = g.append(
                    rows + [rows[0], rows[0]], a["type"], a["componentType"]
                )
            p["attributes"]["TEXCOORD_0"] = g.append(
                [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.0, 0.0), (0.5, 0.5)],
                "VEC2",
                5126,
            )
            p["indices"] = g.append(
                [(i,) for i in [0, 1, 2, 3, 1, 2, 4, 1, 2]], "SCALAR", 5123
            )
            g.write(source)
            before = module.GLB(source)
            report = module.optimize(source, target)
            self.assertEqual(report["vertices_before"], 5)
            self.assertEqual(report["vertices_after"], 4)
            after = module.GLB(target)
            q = after.doc["meshes"][0]["primitives"][0]
            for attribute in ("POSITION", "TEXCOORD_0"):
                original = before.read(p["attributes"][attribute])
                compacted = after.read(q["attributes"][attribute])
                self.assertEqual(
                    [original[i[0]] for i in before.read(p["indices"])],
                    [compacted[i[0]] for i in after.read(q["indices"])],
                )


if __name__ == "__main__":
    unittest.main()
