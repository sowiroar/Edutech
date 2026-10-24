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
    def fixture(self, directory, character="ELIAN"):
        sections = 7 if character in ("NOA", "NOVA") else 4
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
                    for _ in range(sections)
                ],
            }
        ]
        names = ["skin", "MI_Teeth_Baked", "MI_EyeL_Baked", "MI_EyeR_Baked"]
        if sections == 7:
            names += [
                "MI_Face_EyeShell",
                "MI_Face_EyelashesHiLODs",
                "MI_Face_LacrimalFluid",
            ]
        (directory / "export.json").write_text(
            json.dumps({"face_material_sidecars": names})
        )
        for section in range(1, sections):
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
            side.write(directory / f"{character.lower()}-face-material-{section}.glb")
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

    def test_family_face_layouts_keep_all_original_sections_and_uvs(self):
        for character, sections in [("NOA", 7), ("NOVA", 7), ("ATLAS", 4)]:
            with (
                self.subTest(character=character),
                tempfile.TemporaryDirectory() as temp,
            ):
                directory = Path(temp)
                glb = self.fixture(directory, character)
                original_positions = [
                    p["attributes"]["POSITION"]
                    for p in glb.doc["meshes"][0]["primitives"]
                ]
                report = append_face_materials(glb, directory, character)
                self.assertEqual(len(report), sections - 1)
                self.assertEqual(len(glb.doc["materials"]), sections)
                for index, primitive in enumerate(glb.doc["meshes"][0]["primitives"]):
                    self.assertEqual(
                        primitive["attributes"]["POSITION"], original_positions[index]
                    )
                    self.assertEqual(primitive["material"], index)
                    if index:
                        self.assertIn("TEXCOORD_1", primitive["attributes"])

    def test_selects_section_material_when_unreal_bakes_separate_atlases(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            g = self.fixture(directory, "NOA")
            path = directory / "noa-face-material-2.glb"
            side = GLB(path)
            expected = copy.deepcopy(side.doc["materials"][0])
            expected["name"] += "_section2"
            side.doc["materials"] = [{"name": "unrelated"}, expected]
            side.doc["meshes"][0]["primitives"][2]["material"] = 1
            side.write(path)
            report = append_face_materials(g, directory, "NOA")
            self.assertEqual(report[1]["material"], "MI_EyeL_Baked_section2")

    def test_rejects_wrong_material_on_requested_section(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            g = self.fixture(directory, "NOA")
            path = directory / "noa-face-material-2.glb"
            side = GLB(path)
            side.doc["materials"].append({"name": "wrong"})
            side.doc["meshes"][0]["primitives"][2]["material"] = 1
            side.write(path)
            with self.assertRaisesRegex(ValueError, "original face material"):
                append_face_materials(g, directory, "NOA")
