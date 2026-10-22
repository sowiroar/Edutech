import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from elian_materials_glb import append_face_materials
from optimize_nexo_glb import GLB


class ElianMaterialTests(unittest.TestCase):
    def fixture(self, directory):
        g = object.__new__(GLB)
        g.binary = bytearray()
        g.doc = {
            "asset": {"version": "2.0"},
            "accessors": [],
            "bufferViews": [],
            "materials": [{"name": "skin"}],
            "images": [],
            "textures": [],
            "samplers": [{"wrapS": 33071}],
            "meshes": [],
        }
        position = g.append(
            [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], "VEC3", 5126
        )
        indices = g.append([(0,), (1,), (2,)], "SCALAR", 5123)
        g.doc["meshes"] = [
            {
                "name": "Face",
                "primitives": [
                    {
                        "attributes": {"POSITION": position},
                        "indices": indices,
                        "material": 0,
                    }
                    for _ in range(4)
                ],
            }
        ]
        names = ["skin", "MI_Teeth_Baked", "MI_EyeL_Baked", "MI_EyeR_Baked"]
        (directory / "export.json").write_text(
            json.dumps({"face_material_sidecars": names})
        )
        for section in range(1, 4):
            side = copy.deepcopy(g)
            uv = side.append([(0.2, 0.3), (0.8, 0.3), (0.2, 0.9)], "VEC2", 5126)
            for p in side.doc["meshes"][0]["primitives"]:
                p["attributes"]["TEXCOORD_1"] = uv
            content = f"embedded-original-texture-{section}".encode()
            view = len(side.doc["bufferViews"])
            side.doc["bufferViews"].append(
                {
                    "buffer": 0,
                    "byteOffset": len(side.binary),
                    "byteLength": len(content),
                }
            )
            side.binary.extend(content)
            side.doc["materials"] = [
                {
                    "name": names[section],
                    "pbrMetallicRoughness": {
                        "baseColorTexture": {"index": 0, "texCoord": 1}
                    },
                }
            ]
            side.doc["textures"] = [{"source": 0, "sampler": 0}]
            side.doc["images"] = [{"bufferView": view, "mimeType": "image/png"}]
            side.write(directory / f"elian-face-material-{section}.glb")
        return g

    def test_restores_each_original_material_and_bake_uv_without_changing_geometry(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            g = self.fixture(directory)
            old = copy.deepcopy(g.doc["meshes"][0]["primitives"])
            report = append_face_materials(g, directory)
            self.assertEqual(len(report), 3)
            for index, p in enumerate(g.doc["meshes"][0]["primitives"]):
                self.assertEqual(
                    p["attributes"]["POSITION"], old[index]["attributes"]["POSITION"]
                )
                self.assertEqual(p["indices"], old[index]["indices"])
                self.assertEqual(p["material"], index)
                if not index:
                    continue
                texture_info = g.doc["materials"][index]["pbrMetallicRoughness"][
                    "baseColorTexture"
                ]
                self.assertEqual(texture_info["texCoord"], 1)
                self.assertEqual(len(g.read(p["attributes"]["TEXCOORD_1"])), 3)
                texture = g.doc["textures"][texture_info["index"]]
                self.assertEqual(texture["sampler"], index)
                image = g.doc["images"][texture["source"]]
                view = g.doc["bufferViews"][image["bufferView"]]
                self.assertEqual(
                    g.binary[
                        view["byteOffset"] : view["byteOffset"] + view["byteLength"]
                    ],
                    f"embedded-original-texture-{index}".encode(),
                )

    def test_rejects_material_baked_for_another_geometry(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            g = self.fixture(directory)
            p = g.doc["meshes"][0]["primitives"][1]
            p["attributes"]["POSITION"] = g.append([(2.0, 0.0, 0.0)] * 3, "VEC3", 5126)
            with self.assertRaisesRegex(ValueError, "vertices differ"):
                append_face_materials(g, directory)
