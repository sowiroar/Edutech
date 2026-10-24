"""Embed the original Unreal skin color where virtual-texture baking fails."""

import io
import json
from pathlib import Path


def restore_family_skin(glb, directory, character):
    from PIL import Image

    expected = {
        "NOA": "M_Noa_AlternateSkin",
        "NOVA": "M_Nova_SoftSkin",
        "ATLAS": "M_Atlas_MatureSkin",
    }[character]
    sources = json.loads((Path(directory) / "skin-sources.json").read_text())
    records = [r for r in sources if r["material"].rsplit(".", 1)[-1] == expected]
    if not records:
        raise ValueError(f"Missing original skin source for {character}")
    color = [
        t
        for t in records[0]["textures"]
        if "_BC" in t["file"]
        or "BaseColor" in t["file"]
        or t["file"] == "T_NexoMateo_Face1K.tga"
    ]
    if len(color) != 1:
        raise ValueError(f"Ambiguous original skin color for {character}")
    texture = color[0]
    path = Path(directory) / texture["file"]
    if path.parent != Path(directory) or not path.is_file():
        raise ValueError("Missing local original skin image")
    doc = glb.doc
    face = next(m for m in doc["meshes"] if m.get("name") == "Face")["primitives"][0]
    material = doc["materials"][face["material"]]
    if material["name"] != expected:
        raise ValueError("Original face section/material identity mismatch")
    if "TEXCOORD_0" not in face["attributes"]:
        raise ValueError("Missing original face UVs")
    image = Image.open(path).convert("RGB")
    image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    data = io.BytesIO()
    image.save(data, format="JPEG", quality=92)
    content = data.getvalue()
    glb.binary.extend(b"\x00" * (-len(glb.binary) % 4))
    offset = len(glb.binary)
    glb.binary.extend(content)
    doc = glb.doc
    view = len(doc["bufferViews"])
    doc["bufferViews"].append(
        {"buffer": 0, "byteOffset": offset, "byteLength": len(content)}
    )
    image_id = len(doc.setdefault("images", []))
    doc["images"].append({"bufferView": view, "mimeType": "image/jpeg"})
    texture_id = len(doc.setdefault("textures", []))
    doc["textures"].append({"source": image_id})
    material["pbrMetallicRoughness"] = {
        "baseColorTexture": {"index": texture_id},
        "metallicFactor": 0,
        "roughnessFactor": 0.72,
    }
    # Pre-skinned procedural masks cannot be baked reliably. The browser applies
    # their retained cutoff in original centimetres, before skinning.
    material["alphaMode"] = "OPAQUE"
    material.pop("alphaCutoff", None)
    material.pop("normalTexture", None)
    material.setdefault("extras", {})["vivaMaterial"] = (
        character.lower() + "-original-skin-v1"
    )
    return {"source": texture["asset"], "size": list(image.size), "material": expected}
