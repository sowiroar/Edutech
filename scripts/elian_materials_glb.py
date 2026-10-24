"""Restore ELIAN's exported face slots using its own material bakes and UVs."""

import copy
import json
from pathlib import Path


def append_face_materials(glb, directory, character="ELIAN"):
    from optimize_nexo_glb import GLB

    directory = Path(directory)
    audit = json.loads((directory / "export.json").read_text(encoding="utf-8"))
    original = audit.get("face_material_sidecars", [])
    faces = [m for m in glb.doc["meshes"] if m.get("name") == "Face"]
    sections = 7 if character in ("NOA", "NOVA") else 4
    if (
        len(faces) != 1
        or len(faces[0]["primitives"]) != sections
        or len(original) != sections
    ):
        raise ValueError(
            f"{character} face/material layout changed; review before packing"
        )
    report = []
    expected_materials = ["MI_Teeth_Baked", "MI_EyeL_Baked", "MI_EyeR_Baked"]
    if sections == 7:
        expected_materials += [
            "MI_Face_EyeShell",
            "MI_Face_EyelashesHiLODs",
            "MI_Face_LacrimalFluid",
        ]
    for section, expected in enumerate(expected_materials, 1):
        if not original[section].rsplit(".", 1)[-1].startswith(expected):
            raise ValueError("Unexpected ELIAN source material")
        side = GLB(directory / f"{character.lower()}-face-material-{section}.glb")
        target = faces[0]["primitives"][section]
        meshes = side.doc.get("meshes", [])
        if len(meshes) != 1 or len(meshes[0]["primitives"]) != sections:
            raise ValueError(
                "Material must be baked on the original face, not a preview sphere"
            )
        source = meshes[0]["primitives"][section]
        # Unreal may bake a distinct material/atlas for every face section.
        # Select the material actually referenced by this section, not slot zero.
        materials = side.doc.get("materials", [])
        material_index = source.get("material")
        if not isinstance(material_index, int) or not 0 <= material_index < len(
            materials
        ):
            raise ValueError("Face sidecar section has no valid original material")
        material = copy.deepcopy(materials[material_index])
        if not material.get("name", "").startswith(expected):
            raise ValueError("Sidecar does not contain the original face material")
        # Texture baking can add UV1. Copy its UVs only after verifying the exact
        # original topology/vertex order. Never replace geometry or skin weights.
        for key in ("POSITION",):
            if glb.read(target["attributes"][key]) != side.read(
                source["attributes"][key]
            ):
                raise ValueError("Face vertices differ from the material bake")
        if glb.read(target["indices"]) != side.read(source["indices"]):
            raise ValueError("Face indices differ from the material bake")
        for key, index in source["attributes"].items():
            if not key.startswith("TEXCOORD_"):
                continue
            accessor = side.doc["accessors"][index]
            target["attributes"][key] = glb.append(
                side.read(index), accessor["type"], 5126
            )

        image_map, sampler_map, texture_map = {}, {}, {}
        for index, image in enumerate(side.doc.get("images", [])):
            if "uri" in image or "bufferView" not in image:
                raise ValueError("Face textures must be embedded")
            view = side.doc["bufferViews"][image["bufferView"]]
            if view.get("buffer", 0) != 0:
                raise ValueError("Unexpected texture buffer")
            start = view.get("byteOffset", 0)
            content = side.binary[start : start + view["byteLength"]]
            if len(content) != view["byteLength"]:
                raise ValueError("Truncated face texture")
            glb.binary.extend(b"\x00" * (-len(glb.binary) % 4))
            offset = len(glb.binary)
            glb.binary.extend(content)
            imported = copy.deepcopy(image)
            imported["bufferView"] = len(glb.doc["bufferViews"])
            glb.doc["bufferViews"].append(
                {"buffer": 0, "byteOffset": offset, "byteLength": len(content)}
            )
            image_map[index] = len(glb.doc.setdefault("images", []))
            glb.doc["images"].append(imported)
        for index, sampler in enumerate(side.doc.get("samplers", [])):
            sampler_map[index] = len(glb.doc.setdefault("samplers", []))
            glb.doc["samplers"].append(copy.deepcopy(sampler))
        for index, texture in enumerate(side.doc.get("textures", [])):
            if "source" not in texture or texture.get("extensions"):
                raise ValueError("Unsupported face texture encoding")
            imported = copy.deepcopy(texture)
            imported["source"] = image_map[texture["source"]]
            if "sampler" in imported:
                imported["sampler"] = sampler_map[texture["sampler"]]
            texture_map[index] = len(glb.doc.setdefault("textures", []))
            glb.doc["textures"].append(imported)

        def remap_textures(
            value, texture_map=texture_map, attributes=target["attributes"]
        ):
            if isinstance(value, dict):
                for key, item in value.items():
                    if (
                        key.endswith("Texture")
                        and isinstance(item, dict)
                        and "index" in item
                    ):
                        item["index"] = texture_map[item["index"]]
                        uv = (
                            item.get("extensions", {})
                            .get("KHR_texture_transform", {})
                            .get("texCoord", item.get("texCoord", 0))
                        )
                        if f"TEXCOORD_{uv}" not in attributes:
                            raise ValueError(
                                "Original material requires missing UV coordinates"
                            )
                    else:
                        remap_textures(item)
            elif isinstance(value, list):
                for item in value:
                    remap_textures(item)

        remap_textures(material)
        target["material"] = len(glb.doc["materials"])
        glb.doc["materials"].append(material)
        for field in ("extensionsUsed", "extensionsRequired"):
            for extension in side.doc.get(field, []):
                if extension not in glb.doc.setdefault(field, []):
                    glb.doc[field].append(extension)
        report.append(
            {
                "section": section,
                "source": original[section],
                "material": material["name"],
            }
        )
    return report
