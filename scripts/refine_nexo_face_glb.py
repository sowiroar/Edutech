"""Refine Mateo's lightweight web face without replacing its identity or rig.

One normal-guided subdivision pass. Existing vertices and open boundaries stay
fixed; skin weights and UVs interpolate along each edge. This is surface smoothing,
not reconstruction of a missing higher MetaHuman LOD.
"""

import copy
import math
from pathlib import Path


def restore_original_color(glb, directory):
    from optimize_nexo_glb import GLB

    side = GLB(Path(directory) / "nexo-original-color.glb")
    materials = side.doc["materials"]
    if len(materials) != 1 or materials[0].get("name") != "M_NexoMateo_StylizedFace":
        raise ValueError(
            "Expected the saved NEXO face color, not another character material"
        )
    face = next(m for m in glb.doc["meshes"] if m.get("name") == "Face")["primitives"][
        0
    ]
    source = side.doc["meshes"][0]["primitives"][0]
    if glb.read(face["attributes"]["POSITION"]) != side.read(
        source["attributes"]["POSITION"]
    ):
        raise ValueError("NEXO color bake uses different face geometry")
    info = copy.deepcopy(materials[0]["pbrMetallicRoughness"]["baseColorTexture"])
    uv = (
        info.get("extensions", {})
        .get("KHR_texture_transform", {})
        .get("texCoord", info.get("texCoord", 0))
    )
    key = f"TEXCOORD_{uv}"
    if glb.read(face["attributes"][key]) != side.read(source["attributes"][key]):
        raise ValueError("NEXO color bake uses different UV coordinates")
    texture = copy.deepcopy(side.doc["textures"][info["index"]])
    image = copy.deepcopy(side.doc["images"][texture["source"]])
    if "uri" in image or texture.get("extensions"):
        raise ValueError("Expected an embedded NEXO color texture")
    view = side.doc["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    content = side.binary[start : start + view["byteLength"]]
    if len(content) != view["byteLength"]:
        raise ValueError("Truncated face color")
    glb.binary.extend(b"\x00" * (-len(glb.binary) % 4))
    offset = len(glb.binary)
    glb.binary.extend(content)
    image["bufferView"] = len(glb.doc["bufferViews"])
    glb.doc["bufferViews"].append(
        {"buffer": 0, "byteOffset": offset, "byteLength": len(content)}
    )
    texture["source"] = len(glb.doc["images"])
    glb.doc["images"].append(image)
    if "sampler" in texture:
        sampler = copy.deepcopy(side.doc["samplers"][texture["sampler"]])
        texture["sampler"] = len(glb.doc.setdefault("samplers", []))
        glb.doc["samplers"].append(sampler)
    info["index"] = len(glb.doc["textures"])
    glb.doc["textures"].append(texture)
    glb.doc["materials"][face["material"]]["pbrMetallicRoughness"][
        "baseColorTexture"
    ] = info
    for extension in side.doc.get("extensionsUsed", []):
        if extension not in glb.doc.setdefault("extensionsUsed", []):
            glb.doc["extensionsUsed"].append(extension)
    return {
        "material": materials[0]["name"],
        "bytes": len(content),
        "uvs_verified": True,
    }


def refine_nexo_face(glb):
    face = next(m for m in glb.doc["meshes"] if m.get("name") == "Face")
    before = after = 0
    for primitive in face["primitives"]:
        attrs = primitive["attributes"]
        columns = {name: glb.read(index) for name, index in attrs.items()}
        positions = columns["POSITION"]
        normals = columns.get("NORMAL")
        indices = [row[0] for row in glb.read(primitive["indices"])]
        before += len(indices) // 3
        edges = {}
        for start in range(0, len(indices), 3):
            a, b, c = indices[start : start + 3]
            for pair in ((a, b), (b, c), (c, a)):
                key = tuple(sorted(pair))
                edges[key] = edges.get(key, 0) + 1
        weights = []
        joint_sets = [i for i in range(4) if f"JOINTS_{i}" in columns]
        for vertex in range(len(positions)):
            weights.append({})
            for i in joint_sets:
                for joint, value in zip(
                    columns[f"JOINTS_{i}"][vertex], columns[f"WEIGHTS_{i}"][vertex]
                ):
                    if value > 0:
                        weights[-1][int(joint)] = weights[-1].get(int(joint), 0) + value
        output = {
            key: list(rows)
            for key, rows in columns.items()
            if not key.startswith(("JOINTS_", "WEIGHTS_"))
        }
        target_columns = [
            {key: glb.read(index) for key, index in target.items()}
            for target in primitive.get("targets", [])
        ]
        target_output = [
            {key: list(rows) for key, rows in target.items()}
            for target in target_columns
        ]
        edge_ids = {}
        for (a, b), uses in edges.items():
            edge_ids[(a, b)] = len(output["POSITION"])
            for name, rows in output.items():
                value = tuple(
                    (x + y) * 0.5 for x, y in zip(columns[name][a], columns[name][b])
                )
                if name == "POSITION" and normals and uses == 2:
                    delta = tuple(y - x for x, y in zip(positions[a], positions[b]))
                    da = sum(x * y for x, y in zip(delta, normals[a]))
                    db = sum(x * y for x, y in zip(delta, normals[b]))
                    value = tuple(
                        value[i] + (db * normals[b][i] - da * normals[a][i]) * 0.125
                        for i in range(3)
                    )
                if name in ("NORMAL", "TANGENT"):
                    length = math.sqrt(sum(x * x for x in value[:3]))
                    if length > 1e-9:
                        value = tuple(x / length for x in value[:3]) + (
                            (columns[name][a][3],) if name == "TANGENT" else ()
                        )
                rows.append(value)
            blended = {}
            for endpoint in (a, b):
                for joint, value in weights[endpoint].items():
                    blended[joint] = blended.get(joint, 0) + value * 0.5
            weights.append(blended)
            for source, target in zip(target_columns, target_output):
                for key in source:
                    target[key].append(
                        tuple(
                            (x + y) * 0.5
                            for x, y in zip(source[key][a], source[key][b])
                        )
                    )
        refined = []
        for start in range(0, len(indices), 3):
            a, b, c = indices[start : start + 3]
            ab, bc, ca = (
                edge_ids[tuple(sorted(edge))] for edge in ((a, b), (b, c), (c, a))
            )
            refined.extend((a, ab, ca, ab, b, bc, ca, bc, c, ab, bc, ca))
        for name in list(attrs):
            if name.startswith(("JOINTS_", "WEIGHTS_")):
                del attrs[name]
        for name, rows in output.items():
            kind = glb.doc["accessors"][attrs[name]]["type"]
            attrs[name] = glb.append(rows, kind, 5126)
            if name == "POSITION":
                glb.doc["accessors"][attrs[name]].update(
                    min=[min(v[i] for v in rows) for i in range(3)],
                    max=[max(v[i] for v in rows) for i in range(3)],
                )
        if weights and joint_sets:
            count = max(len(w) for w in weights)
            if count > 16:
                raise ValueError("Refined face exceeds supported skin influences")
            ranked = [
                sorted(w.items(), key=lambda x: x[1], reverse=True) for w in weights
            ]
            for i in range((count + 3) // 4):
                joints, values = [], []
                for row in ranked:
                    part = row[i * 4 : i * 4 + 4]
                    joints.append(tuple([j for j, _ in part] + [0] * (4 - len(part))))
                    values.append(tuple([w for _, w in part] + [0.0] * (4 - len(part))))
                attrs[f"JOINTS_{i}"] = glb.append(joints, "VEC4", 5123)
                attrs[f"WEIGHTS_{i}"] = glb.append(values, "VEC4", 5126)
        for source, target in zip(primitive.get("targets", []), target_output):
            for name, rows in target.items():
                source[name] = glb.append(
                    rows, glb.doc["accessors"][source[name]]["type"], 5126
                )
        primitive["indices"] = glb.append(
            [(i,) for i in refined],
            "SCALAR",
            5123 if len(output["POSITION"]) <= 65535 else 5125,
        )
        after += len(refined) // 3
    return {
        "method": "one normal-guided pass; original vertices and boundaries retained",
        "triangles_before": before,
        "triangles_after": after,
    }
