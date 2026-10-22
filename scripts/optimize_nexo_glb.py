"""Prepare the exported NEXO rig for Three.js without modifying Unreal assets."""

import copy
import io
import json
import struct
from pathlib import Path

FORMATS = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
DIMENSIONS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class GLB:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        magic, version, length = struct.unpack_from("<4sII", raw)
        if magic != b"glTF" or version != 2 or length != len(raw):
            raise ValueError("Invalid GLB")
        size, kind = struct.unpack_from("<II", raw, 12)
        if kind != 0x4E4F534A:
            raise ValueError("Missing JSON chunk")
        self.doc = json.loads(raw[20 : 20 + size])
        bin_size, bin_kind = struct.unpack_from("<II", raw, 20 + size)
        if bin_kind != 0x004E4942:
            raise ValueError("Missing BIN chunk")
        self.binary = bytearray(raw[28 + size : 28 + size + bin_size])

    def read(self, index, normalize=True):
        a = self.doc["accessors"][index]
        if "sparse" in a:
            raise ValueError("Sparse accessors need a separate conversion")
        v = self.doc["bufferViews"][a["bufferView"]]
        fmt = "<" + FORMATS[a["componentType"]] * DIMENSIONS[a["type"]]
        stride = v.get("byteStride", struct.calcsize(fmt))
        start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        rows = [
            struct.unpack_from(fmt, self.binary, start + i * stride)
            for i in range(a["count"])
        ]
        if normalize and a.get("normalized"):
            div = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535}[a["componentType"]]
            rows = [tuple(max(-1, value / div) for value in row) for row in rows]
        return rows

    def append(self, rows, kind, component_type):
        self.binary.extend(b"\x00" * (-len(self.binary) % 4))
        start = len(self.binary)
        fmt = "<" + FORMATS[component_type] * DIMENSIONS[kind]
        for row in rows:
            self.binary.extend(struct.pack(fmt, *row))
        view = len(self.doc["bufferViews"])
        self.doc["bufferViews"].append(
            {"buffer": 0, "byteOffset": start, "byteLength": len(self.binary) - start}
        )
        index = len(self.doc["accessors"])
        self.doc["accessors"].append(
            {
                "bufferView": view,
                "componentType": component_type,
                "count": len(rows),
                "type": kind,
            }
        )
        return index

    def write(self, path):
        self.doc["buffers"] = [{"byteLength": len(self.binary)}]
        self.binary.extend(b"\x00" * (-len(self.binary) % 4))
        payload = json.dumps(self.doc, separators=(",", ":")).encode()
        payload += b" " * (-len(payload) % 4)
        data = struct.pack("<4sII", b"glTF", 2, 28 + len(payload) + len(self.binary))
        data += struct.pack("<II", len(payload), 0x4E4F534A) + payload
        data += struct.pack("<II", len(self.binary), 0x004E4942) + self.binary
        Path(path).write_bytes(data)


def optimize(source, target, legacy_materials=False, skin_roles=None, character="NEXO"):
    glb = GLB(source)
    d = glb.doc
    report = {
        "source_bytes": Path(source).stat().st_size,
        "skins_before": sum(len(s["joints"]) for s in d["skins"]),
    }
    if character == "LIRA":
        from lira_brows_glb import append_lira_brows

        report["original_eyebrows"] = append_lira_brows(glb, Path(source).parent)
    if character == "ELIAN":
        from elian_materials_glb import append_face_materials

        report["original_face_materials"] = append_face_materials(
            glb, Path(source).parent
        )
    if character == "NEXO" and any(
        m.get("name", "").startswith("MI_Face_Skin_Baked") for m in d["materials"]
    ):
        from refine_nexo_face_glb import refine_nexo_face, restore_original_color

        report["original_face_color"] = restore_original_color(glb, Path(source).parent)
        native_face = Path(source).parent / "nexo-native-lod3.glb"
        if native_face.is_file():
            from native_nexo_face_glb import replace_native_face

            report["native_face"] = replace_native_face(glb, native_face)
        else:
            report["face_surface_refinement"] = refine_nexo_face(glb)
        for material in d["materials"]:
            if material.get("name", "").startswith("MI_Face_Skin_Baked"):
                material.setdefault("extras", {})["vivaMaterial"] = (
                    "nexo-native-face-v2"
                )
    # Compact exact duplicates only, including UVs, normals, skin weights and
    # morphs in the identity. Preserve seams and every triangle's attribute values.
    vertices_before = vertices_after = 0
    for mesh in d["meshes"]:
        for primitive in mesh["primitives"]:
            attrs = primitive["attributes"]
            count = d["accessors"][attrs["POSITION"]]["count"]
            vertices_before += count
            if "indices" not in primitive:
                vertices_after += count
                continue
            index_rows = glb.read(primitive["indices"], normalize=False)
            indices = [row[0] for row in index_rows]
            used = sorted(set(indices))
            if not used or used[0] < 0 or used[-1] >= count:
                raise ValueError("Invalid vertex index in exported mesh")
            groups = [attrs, *primitive.get("targets", [])]
            columns = [
                (attributes, name, accessor_id, glb.read(accessor_id, normalize=False))
                for attributes in groups
                for name, accessor_id in sorted(attributes.items())
            ]
            unique = {}
            selected_indices = []
            mapping = {}
            for old in used:
                key = tuple(rows[old] for _, _, _, rows in columns)
                if key not in unique:
                    unique[key] = len(selected_indices)
                    selected_indices.append(old)
                mapping[old] = unique[key]
            vertices_after += len(selected_indices)
            if len(selected_indices) == count:
                continue
            for attributes, name, accessor_id, rows in columns:
                accessor = d["accessors"][accessor_id]
                selected = [rows[i] for i in selected_indices]
                new_id = glb.append(
                    selected, accessor["type"], accessor["componentType"]
                )
                new_accessor = d["accessors"][new_id]
                if accessor.get("normalized"):
                    new_accessor["normalized"] = True
                for field, fn in [("min", min), ("max", max)]:
                    if field in accessor:
                        new_accessor[field] = [fn(values) for values in zip(*selected)]
                attributes[name] = new_id
            primitive["indices"] = glb.append(
                [(mapping[i],) for i in indices],
                "SCALAR",
                5123 if len(selected_indices) <= 65535 else 5125,
            )
    report["vertices_before"] = vertices_before
    report["vertices_after"] = vertices_after
    for node in d["nodes"]:
        if node.get("name") == "NEXO_UAM_Background":
            node.pop("mesh", None)
    # Compatibility repair for export profile 1. Profile 2 fixes the LOD map in Unreal before baking.
    if legacy_materials:
        materials = {m["name"]: i for i, m in enumerate(d["materials"])}
        face = next(m for m in d["meshes"] if m.get("name") == "Face")
        expected = [
            "M_NexoMateo_StylizedFace",
            "MI_Teeth_Baked",
            "MI_EyeL_Baked_Face",
            "MI_EyeR_Baked_Face",
        ]
        if len(face["primitives"]) != 4:
            raise ValueError("Unexpected legacy face layout")
        for primitive, name in zip(face["primitives"], expected):
            primitive["material"] = materials[name]

    roles = {}
    for s in d["skins"]:
        role = (skin_roles or {}).get(s.get("name"))
        if role is None:
            role = (
                "face"
                if "FaceMesh" in s.get("name", "")
                else "body"
                if "BodyMesh" in s.get("name", "")
                else "clothing"
            )
        roles[role] = {d["nodes"][i]["name"]: i for i in s["joints"]}
        for i in s["joints"]:
            d["nodes"][i].setdefault("extras", {}).update(
                vivaBone=d["nodes"][i]["name"], vivaSkin=role
            )
    # This native Mateo setup uses the body's pose for common face/clothing bones.
    # Copy those tracks directly, including differing reference translations:
    # retaining the face's reference offsets makes its chest intersect the shirt.
    # Facial-only joints keep their own bind transforms for expressions.
    copies = 0
    clothing_copies = 0
    for animation in d.get("animations", []):
        additions = []
        existing = {
            (c["target"]["node"], c["target"]["path"]) for c in animation["channels"]
        }
        for channel in animation["channels"]:
            node_id = channel["target"]["node"]
            n = d["nodes"][node_id]
            if n.get("extras", {}).get("vivaSkin") != "body":
                continue
            for role in ("face", "clothing"):
                target_id = roles.get(role, {}).get(n["name"])
                key = (target_id, channel["target"]["path"])
                if target_id is not None and key not in existing:
                    item = copy.deepcopy(channel)
                    item["target"]["node"] = target_id
                    additions.append(item)
                    existing.add(key)
                    if role == "clothing":
                        clothing_copies += 1
                    else:
                        copies += 1
        animation["channels"].extend(additions)
    report["face_animation_channels_copied"] = copies
    report["clothing_animation_channels_copied"] = clothing_copies
    constant_samplers = 0
    for animation in d.get("animations", []):
        for sampler in animation["samplers"]:
            if sampler.get("interpolation", "LINEAR") not in ("LINEAR", "STEP"):
                continue
            values = glb.read(sampler["output"])
            if len(values) > 1 and all(row == values[0] for row in values[1:]):
                kind = d["accessors"][sampler["output"]]["type"]
                sampler["input"] = glb.append(
                    [glb.read(sampler["input"])[0]], "SCALAR", 5126
                )
                sampler["output"] = glb.append([values[0]], kind, 5126)
                constant_samplers += 1
    report["constant_animation_samplers_compacted"] = constant_samplers

    discarded = []
    for skin_id, skin in enumerate(d["skins"]):
        primitives = [
            p
            for n in d["nodes"]
            if n.get("skin") == skin_id
            for p in d["meshes"][n["mesh"]]["primitives"]
        ]
        used = set()
        converted = []
        for primitive in primitives:
            attrs = primitive["attributes"]
            sets = [
                (glb.read(attrs[f"JOINTS_{i}"]), glb.read(attrs[f"WEIGHTS_{i}"]))
                for i in range(4)
                if f"JOINTS_{i}" in attrs
            ]
            rows = []
            for vertex in range(len(sets[0][0])):
                weights = {}
                for joints, values in sets:
                    for joint, value in zip(joints[vertex], values[vertex]):
                        if value > 0:
                            weights[joint] = weights.get(joint, 0) + value
                ranked = sorted(weights.items(), key=lambda x: x[1], reverse=True)
                total = sum(v for _, v in ranked)
                kept = ranked[:4]
                kept_total = sum(v for _, v in kept)
                if kept_total <= 0:
                    raise ValueError("Unweighted vertex in skinned mesh")
                discarded.append(1 - kept_total / total)
                kept = [(j, w / kept_total) for j, w in kept]
                used.update(j for j, _ in kept)
                rows.append(kept)
            converted.append((attrs, rows))
        indices = sorted(used)
        joint_map = {old: new for new, old in enumerate(indices)}
        ibms = glb.read(skin["inverseBindMatrices"])
        skin["inverseBindMatrices"] = glb.append(
            [ibms[i] for i in indices], "MAT4", 5126
        )
        skin["joints"] = [skin["joints"][i] for i in indices]
        for attrs, rows in converted:
            joints, weights = [], []
            for row in rows:
                joints.append(
                    tuple([joint_map[j] for j, _ in row] + [0] * (4 - len(row)))
                )
                weights.append(tuple([w for _, w in row] + [0.0] * (4 - len(row))))
            for key in list(attrs):
                if key.startswith(("JOINTS_", "WEIGHTS_")):
                    del attrs[key]
            attrs["JOINTS_0"] = glb.append(joints, "VEC4", 5123)
            attrs["WEIGHTS_0"] = glb.append(weights, "VEC4", 5126)
    report["skins_after"] = sum(len(s["joints"]) for s in d["skins"])
    report["discarded_weight_max"] = max(discarded, default=0)
    report["discarded_weight_mean"] = sum(discarded) / max(1, len(discarded))

    # Keep geometry, weighted joints, and their ancestors; discard unused helper leaves.
    parents = {
        child: i for i, n in enumerate(d["nodes"]) for child in n.get("children", [])
    }
    keep = {i for i, n in enumerate(d["nodes"]) if "mesh" in n}
    keep.update(i for skin in d["skins"] for i in skin["joints"])
    keep.update(s["skeleton"] for s in d["skins"] if "skeleton" in s)
    for i in list(keep):
        while i in parents:
            i = parents[i]
            keep.add(i)
    indices = sorted(keep)
    node_map = {old: new for new, old in enumerate(indices)}
    report["nodes_before"], report["nodes_after"] = len(d["nodes"]), len(indices)
    for n in d["nodes"]:
        if "children" in n:
            n["children"] = [node_map[i] for i in n["children"] if i in keep]
    for scene in d["scenes"]:
        scene["nodes"] = [node_map[i] for i in scene["nodes"] if i in keep]
    for skin in d["skins"]:
        skin["joints"] = [node_map[i] for i in skin["joints"]]
        if "skeleton" in skin:
            skin["skeleton"] = node_map[skin["skeleton"]]
    for a in d.get("animations", []):
        a["channels"] = [c for c in a["channels"] if c["target"]["node"] in keep]
        used = sorted({c["sampler"] for c in a["channels"]})
        sample_map = {old: new for new, old in enumerate(used)}
        a["samplers"] = [a["samplers"][i] for i in used]
        for c in a["channels"]:
            c["target"]["node"] = node_map[c["target"]["node"]]
            c["sampler"] = sample_map[c["sampler"]]
    d["nodes"] = [d["nodes"][i] for i in indices]
    face_bones = {
        n.get("extras", {}).get("vivaBone")
        for n in d["nodes"]
        if n.get("extras", {}).get("vivaSkin") == "face"
    }
    report["has_mouth_rig"] = {
        "FACIAL_C_Jaw",
        "FACIAL_C_LowerLipRotation",
        "FACIAL_C_LipLower",
        "FACIAL_L_Eye",
        "FACIAL_R_Eye",
    }.issubset(face_bones)

    def prune_array(name, references):
        ids = sorted({obj[key] for obj, key in references})
        mapping = {old: new for new, old in enumerate(ids)}
        d[name] = [d[name][i] for i in ids]
        for obj, key in references:
            obj[key] = mapping[obj[key]]

    prune_array("meshes", [(n, "mesh") for n in d["nodes"] if "mesh" in n])
    primitives = [p for m in d["meshes"] for p in m["primitives"]]
    prune_array("materials", [(p, "material") for p in primitives if "material" in p])
    for material in d["materials"]:
        if character == "ELIAN":
            if material.get("name") == "M_ELIAN_Uniform":
                material.setdefault("extras", {})["vivaMaterial"] = (
                    "elian-native-uniform-v1"
                )
                material.pop("normalTexture", None)
                material["pbrMetallicRoughness"] = {
                    "baseColorFactor": [1, 1, 1, 1],
                    "roughnessFactor": 0.82,
                    "metallicFactor": 0,
                }
            if material.get("name", "").startswith("MI_Face_Skin_Baked"):
                material.setdefault("extras", {})["vivaMaterial"] = (
                    "elian-native-face-v1"
                )
        if character == "LIRA":
            if material.get("name") == "MI_Face_EyeShell":
                # UE's eye-shadow shell bakes as opaque black in glTF. The
                # actual eyeballs retain Juan's original iris textures below it.
                material["pbrMetallicRoughness"] = {"baseColorFactor": [0, 0, 0, 0]}
                material["alphaMode"] = "BLEND"
            if material.get("name") == "MI_Face_LacrimalFluid":
                material["pbrMetallicRoughness"]["baseColorFactor"] = [1, 1, 1, 0.12]
            if material.get("name") == "M_Lira_Uniform":
                # Preserve Juan's two-UV procedural fabric in the web shader.
                # A glTF texture bake cannot represent its overlapping front/back UVs.
                material.setdefault("extras", {})["vivaMaterial"] = (
                    "lira-juan-uniform-v1"
                )
                material.pop("normalTexture", None)
                material["pbrMetallicRoughness"] = {
                    "baseColorFactor": [1, 1, 1, 1],
                    "roughnessFactor": 0.82,
                    "metallicFactor": 0,
                }
            if "MI_Lira_Face_Skin" in material.get("name", ""):
                material.setdefault("extras", {})["vivaMaterial"] = "lira-juan-face-v1"
        for extension in ("KHR_materials_specular", "KHR_materials_anisotropy"):
            material.get("extensions", {}).pop(extension, None)
    texture_refs = []

    def textures(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if (
                    key.endswith("Texture")
                    and isinstance(value, dict)
                    and "index" in value
                ):
                    texture_refs.append((value, "index"))
                else:
                    textures(value)
        elif isinstance(obj, list):
            for value in obj:
                textures(value)

    textures(d["materials"])
    prune_array("textures", texture_refs)
    prune_array("images", [(t, "source") for t in d["textures"]])
    texture_bytes_before = texture_bytes_after = 0
    resized_images = []
    if d["images"]:
        from PIL import Image

        for image in d["images"]:
            view = d["bufferViews"][image["bufferView"]]
            start = view.get("byteOffset", 0)
            with Image.open(
                io.BytesIO(glb.binary[start : start + view["byteLength"]])
            ) as decoded:
                width, height = decoded.size
                texture_bytes_before += width * height * 4 * 4 / 3
                if max(width, height) > 1024:
                    decoded.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                    encoded = io.BytesIO()
                    # Lossless encoding preserves normal-map channels and hair alpha.
                    decoded.save(encoded, format="PNG")
                    content = encoded.getvalue()
                    glb.binary.extend(b"\x00" * (-len(glb.binary) % 4))
                    offset = len(glb.binary)
                    glb.binary.extend(content)
                    image["bufferView"] = len(d["bufferViews"])
                    image["mimeType"] = "image/png"
                    d["bufferViews"].append(
                        {"buffer": 0, "byteOffset": offset, "byteLength": len(content)}
                    )
                    resized_images.append(
                        {
                            "name": image.get("name"),
                            "before": [width, height],
                            "after": list(decoded.size),
                        }
                    )
                texture_bytes_after += decoded.width * decoded.height * 4 * 4 / 3
    report["texture_bytes_estimate_before"] = round(texture_bytes_before)
    report["texture_bytes_estimate_after"] = round(texture_bytes_after)
    report["resized_images"] = resized_images
    refs = [(s, "inverseBindMatrices") for s in d["skins"]]
    for p in primitives:
        if "indices" in p:
            refs.append((p, "indices"))
        refs.extend((p["attributes"], k) for k in p["attributes"])
        for target_attrs in p.get("targets", []):
            refs.extend((target_attrs, k) for k in target_attrs)
    for a in d.get("animations", []):
        refs.extend((s, key) for s in a["samplers"] for key in ("input", "output"))
    prune_array("accessors", refs)
    prune_array(
        "bufferViews",
        [(a, "bufferView") for a in d["accessors"]]
        + [(i, "bufferView") for i in d["images"]],
    )
    packed = bytearray()
    for view in d["bufferViews"]:
        packed.extend(b"\x00" * (-len(packed) % 4))
        start = view.get("byteOffset", 0)
        view["byteOffset"] = len(packed)
        packed.extend(glb.binary[start : start + view["byteLength"]])
    glb.binary = packed
    d["extensionsUsed"] = [
        e
        for e in d.get("extensionsUsed", [])
        if e not in ("KHR_materials_specular", "KHR_materials_anisotropy")
    ]
    glb.write(target)
    report["output_bytes"] = Path(target).stat().st_size
    return report
