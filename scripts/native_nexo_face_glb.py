"""Use Mateo's original DNA LOD3 geometry with his saved Unreal face rig.

The UE 5.8 DNA translator's default coordinate configuration emits Z-up
geometry, whereas the assembled GLB uses Y-up. Only geometry is converted;
the original assembled skeleton, bind matrices and animation stay authoritative.
"""

import math
from pathlib import Path


def replace_native_face(glb, path):
    from optimize_nexo_glb import GLB

    native = GLB(Path(path))
    face_index = next(
        i for i, m in enumerate(glb.doc["meshes"]) if m.get("name") == "Face"
    )
    face = glb.doc["meshes"][face_index]
    mesh_node = next(n for n in glb.doc["nodes"] if n.get("mesh") == face_index)
    skin = glb.doc["skins"][mesh_node["skin"]]
    if skin.get("name") != "SKM_CH_Nexo_MateoNative_FaceMesh":
        raise ValueError(
            "Native geometry is only valid for the original Mateo face rig"
        )
    if len(face["primitives"]) != 4 or len(native.doc["skins"]) != 1:
        raise ValueError("Unexpected original face layout")
    native_mesh = native.doc["meshes"][0]
    triangle_counts = [
        native.doc["accessors"][p["indices"]]["count"] // 3
        for p in native_mesh["primitives"]
    ]
    if triangle_counts[:4] != [5048, 796, 216, 216]:
        raise ValueError("Expected original MetaHuman LOD3 skin, teeth and eyes")
    source_skin = native.doc["skins"][0]
    original_names = {
        glb.doc["nodes"][n]["name"]: i for i, n in enumerate(skin["joints"])
    }
    remap = {
        i: original_names[native.doc["nodes"][n]["name"]]
        for i, n in enumerate(source_skin["joints"])
    }
    report = {
        "source": "CH_Nexo_MateoNative original head DNA; native LOD3",
        "skin_triangles": 5048,
        "retained_original_skeleton": True,
        "geometry_coordinate_conversion": "XYZ to XZY; original assembled bind matrices retained",
        "primitives": [],
    }
    replaced = []
    for original, source in zip(face["primitives"], native_mesh["primitives"][:4]):
        attributes = {}
        positions = []
        normals = []
        for key, accessor_id in source["attributes"].items():
            if key == "TANGENT":
                # Let the browser derive tangents from the converted surface and UVs.
                continue
            accessor = native.doc["accessors"][accessor_id]
            rows = native.read(accessor_id)
            if key in ("POSITION", "NORMAL"):
                rows = [(x, z, y) for x, y, z in rows]
                if key == "POSITION":
                    positions = rows
                else:
                    normals = rows
            if key.startswith("JOINTS_"):
                rows = [tuple(remap[int(i)] for i in row) for row in rows]
            component_type = 5123 if key.startswith("JOINTS_") else 5126
            attributes[key] = glb.append(rows, accessor["type"], component_type)
            if key == "POSITION":
                bounds = {
                    "min": [min(v[i] for v in rows) for i in range(3)],
                    "max": [max(v[i] for v in rows) for i in range(3)],
                }
                glb.doc["accessors"][attributes[key]].update(bounds)
                old_positions = glb.read(original["attributes"]["POSITION"])
                error = max(
                    abs(bounds[k][i] - fn(v[i] for v in old_positions))
                    for k, fn in [("min", min), ("max", max)]
                    for i in range(3)
                )
                if error > 0.003:
                    raise ValueError(
                        f"Native face bounds differ from Mateo by {error:.4f} m"
                    )
        indices = [row[0] for row in native.read(source["indices"])]
        positive = negative = 0
        for k in range(0, len(indices), 3):
            a, b, c = (positions[i] for i in indices[k : k + 3])
            ab = [y - x for x, y in zip(a, b)]
            ac = [y - x for x, y in zip(a, c)]
            cross = (
                ab[1] * ac[2] - ab[2] * ac[1],
                ab[2] * ac[0] - ab[0] * ac[2],
                ab[0] * ac[1] - ab[1] * ac[0],
            )
            dot = sum(x * y for x, y in zip(cross, normals[indices[k]]))
            positive += dot > 1e-12
            negative += dot < -1e-12
        if negative > positive:
            indices = [
                v
                for k in range(0, len(indices), 3)
                for v in (indices[k], indices[k + 2], indices[k + 1])
            ]
        if max(positive, negative) / max(1, positive + negative) < 0.98:
            raise ValueError("Inconsistent native face winding or normals")
        if not all(math.isfinite(v) for row in positions for v in row):
            raise ValueError("Invalid native coordinates")
        primitive = {
            "attributes": attributes,
            "material": original["material"],
            "indices": glb.append([(i,) for i in indices], "SCALAR", 5125),
        }
        replaced.append(primitive)
        report["primitives"].append(
            {
                "triangles": len(indices) // 3,
                "bounds_error_m": error,
                "winding_agreement": max(positive, negative)
                / max(1, positive + negative),
            }
        )
    face["primitives"] = replaced
    return report
