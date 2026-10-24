"""Preserve the original SlightArch cards on Lira's web facial skeleton."""

import copy
import io
from pathlib import Path


def append_lira_brows(glb, directory):
    from PIL import Image

    cards_path = Path(directory) / "lira-brows.glb"
    atlas_path = Path(directory) / "lira-brows-attribute.tga"
    if not cards_path.is_file() or not atlas_path.is_file():
        raise ValueError(
            "Export Lira original eyebrow cards and atlas before installation"
        )
    cards = type(glb)(cards_path)
    d = glb.doc
    face_mesh = next(
        i for i, mesh in enumerate(d["meshes"]) if mesh.get("name") == "Face"
    )
    face_node = next(
        i for i, node in enumerate(d["nodes"]) if node.get("mesh") == face_mesh
    )
    face_attrs = d["meshes"][face_mesh]["primitives"][0]["attributes"]
    positions = glb.read(face_attrs["POSITION"])
    # Transfer only the original face's bone weights. Card geometry/UVs retain
    # Juan's assembled SlightArch shape instead of drawing replacement eyebrows.
    primitive = cards.doc["meshes"][0]["primitives"][0]
    card_positions = cards.read(primitive["attributes"]["POSITION"])
    candidates = [
        (i, p) for i, p in enumerate(positions) if 1.64 < p[1] < 1.76 and p[2] > 0.06
    ]
    if not candidates:
        raise ValueError("Unexpected Lira face coordinates")
    nearest = [
        min(candidates, key=lambda v: sum((a - b) ** 2 for a, b in zip(p, v[1])))[0]
        for p in card_positions
    ]
    distance = [
        sum((a - b) ** 2 for a, b in zip(p, positions[i])) ** 0.5
        for p, i in zip(card_positions, nearest)
    ]
    # Groom binding fits these stock cards to the assembled face in Unreal.
    # Reproduce that fit on its front surface, keeping each strand's XY layout.
    face_indices = [
        v[0] for v in glb.read(d["meshes"][face_mesh]["primitives"][0]["indices"])
    ]
    triangles = [
        tuple(positions[i] for i in face_indices[j : j + 3])
        for j in range(0, len(face_indices), 3)
    ]
    triangles = [
        t
        for t in triangles
        if min(p[1] for p in t) < 1.76
        and max(p[1] for p in t) > 1.64
        and min(p[2] for p in t) > 0.06
    ]
    fitted = []
    for x, y, z in card_positions:
        hits = []
        for a, b, c in triangles:
            det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(det) < 1e-12:
                continue
            u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / det
            v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / det
            if u >= -0.00001 and v >= -0.00001 and u + v <= 1.00001:
                hits.append(u * a[2] + v * b[2] + (1 - u - v) * c[2])
        fitted.append((x, y, max(hits) + 0.0007 if hits else z + 0.003))
    attrs = {}
    for name, accessor_id in primitive["attributes"].items():
        accessor = cards.doc["accessors"][accessor_id]
        new_id = glb.append(
            cards.read(accessor_id, normalize=False),
            accessor["type"],
            accessor["componentType"],
        )
        for field in ("min", "max", "normalized"):
            if field in accessor:
                d["accessors"][new_id][field] = accessor[field]
        attrs[name] = new_id
    attrs["POSITION"] = glb.append(fitted, "VEC3", 5126)
    d["accessors"][attrs["POSITION"]].update(
        min=[min(x) for x in zip(*fitted)], max=[max(x) for x in zip(*fitted)]
    )
    for name in ("JOINTS_0", "JOINTS_1", "WEIGHTS_0", "WEIGHTS_1"):
        if name not in face_attrs:
            continue
        values = glb.read(face_attrs[name])
        attrs[name] = glb.append(
            [values[i] for i in nearest],
            "VEC4",
            5123 if name.startswith("JOINTS") else 5126,
        )
    # UE HairCardsAttributeCommon.ush, layout 2: attribute atlas R = coverage.
    atlas = Image.open(atlas_path).convert("RGB")
    rgba = Image.new("RGBA", atlas.size, (255, 255, 255, 255))
    rgba.putalpha(atlas.getchannel("R"))
    stream = io.BytesIO()
    rgba.save(stream, format="PNG")
    payload = stream.getvalue()
    glb.binary.extend(b"\0" * (-len(glb.binary) % 4))
    view = len(d["bufferViews"])
    d["bufferViews"].append(
        {"buffer": 0, "byteOffset": len(glb.binary), "byteLength": len(payload)}
    )
    glb.binary.extend(payload)
    image_id = len(d["images"])
    d["images"].append(
        {
            "name": "Lira_SlightArch_Coverage",
            "bufferView": view,
            "mimeType": "image/png",
        }
    )
    texture_id = len(d["textures"])
    d["textures"].append({"source": image_id})
    material_id = len(d["materials"])
    d["materials"].append(
        {
            "name": "Lira_Original_SlightArch_Brows_Web",
            "doubleSided": True,
            "alphaMode": "MASK",
            "alphaCutoff": 0.08,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": texture_id},
                "baseColorFactor": [0.035, 0.018, 0.009, 0.72],
                "metallicFactor": 0,
                "roughnessFactor": 0.85,
            },
        }
    )
    index_rows = cards.read(primitive["indices"], normalize=False)
    mesh_id = len(d["meshes"])
    d["meshes"].append(
        {
            "name": "Lira_Original_SlightArch_Brows",
            "primitives": [
                {
                    "attributes": attrs,
                    "indices": glb.append(index_rows, "SCALAR", 5123),
                    "material": material_id,
                }
            ],
        }
    )
    node = copy.deepcopy(d["nodes"][face_node])
    node.pop("children", None)
    node["mesh"] = mesh_id
    node["name"] = "Lira_Original_SlightArch_Brows"
    node_id = len(d["nodes"])
    parents = [n["children"] for n in d["nodes"] if face_node in n.get("children", [])]
    parents += [s["nodes"] for s in d["scenes"] if face_node in s.get("nodes", [])]
    if not parents:
        raise ValueError("Missing face parent for eyebrow attachment")
    d["nodes"].append(node)
    for children in parents:
        children.append(node_id)
    return {
        "source": str(cards_path),
        "triangles": len(index_rows) // 3,
        "nearest_face_max_cm": max(distance) * 100,
        "attachment": "existing-face-skin-weights",
    }
