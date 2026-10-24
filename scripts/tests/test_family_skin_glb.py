import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parents[1]))
import test_elian_materials_glb as fixtures
from family_skin_glb import restore_family_skin


class FamilySkinTests(unittest.TestCase):
    def fixture(self, directory):
        glb = fixtures.ElianMaterialTests().fixture(directory, "NOA")
        glb.doc["materials"][0]["name"] = "M_Noa_AlternateSkin"
        face = glb.doc["meshes"][0]["primitives"][0]
        face["attributes"]["TEXCOORD_0"] = glb.append(
            [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)], "VEC2", 5126
        )
        Image.new("RGB", (2048, 2048), (150, 100, 80)).save(directory / "T_Head_BC.tga")
        (directory / "skin-sources.json").write_text(
            json.dumps(
                [
                    {
                        "material": "/Noa/M_Noa_AlternateSkin.M_Noa_AlternateSkin",
                        "textures": [
                            {"asset": "/Noa/T_Head_BC", "file": "T_Head_BC.tga"}
                        ],
                    }
                ]
            )
        )
        return glb

    def test_preserves_geometry_and_uvs_and_bounds_texture_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            glb = self.fixture(directory)
            original = json.dumps(glb.doc["meshes"])
            report = restore_family_skin(glb, directory, "NOA")
            self.assertEqual(report["size"], [1024, 1024])
            self.assertEqual(json.dumps(glb.doc["meshes"]), original)
            self.assertEqual(
                glb.doc["materials"][0]["extras"]["vivaMaterial"],
                "noa-original-skin-v1",
            )
            self.assertEqual(glb.doc["materials"][0]["alphaMode"], "OPAQUE")

    def test_rejects_another_characters_material(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            glb = self.fixture(directory)
            glb.doc["materials"][0]["name"] = "M_Elian_Skin"
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                restore_family_skin(glb, directory, "NOA")
