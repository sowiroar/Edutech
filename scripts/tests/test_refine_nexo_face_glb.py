import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from optimize_nexo_glb import GLB
from refine_nexo_face_glb import refine_nexo_face


class FaceRefinementTests(unittest.TestCase):
    def fixture(self):
        g = object.__new__(GLB)
        g.binary = bytearray()
        g.doc = {"accessors": [], "bufferViews": [], "meshes": []}
        attrs = {}
        for name, rows, kind, component in [
            (
                "POSITION",
                [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
                "VEC3",
                5126,
            ),
            ("NORMAL", [(0.0, 0.0, 1.0)] * 4, "VEC3", 5126),
            (
                "TEXCOORD_0",
                [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
                "VEC2",
                5126,
            ),
            (
                "JOINTS_0",
                [(0, 0, 0, 0), (0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0)],
                "VEC4",
                5123,
            ),
            ("WEIGHTS_0", [(1.0, 0.0, 0.0, 0.0)] * 4, "VEC4", 5126),
        ]:
            attrs[name] = g.append(rows, kind, component)
        primitive = {
            "attributes": attrs,
            "indices": g.append([(i,) for i in (0, 1, 2, 0, 2, 3)], "SCALAR", 5123),
            "targets": [{"POSITION": g.append([(0.0, 0.0, 0.1)] * 4, "VEC3", 5126)}],
        }
        g.doc["meshes"] = [{"name": "Face", "primitives": [primitive]}]
        return g, primitive

    def test_preserves_existing_vertices_boundary_uv_and_morphs(self):
        g, p = self.fixture()
        original = g.read(p["attributes"]["POSITION"])
        report = refine_nexo_face(g)
        positions = g.read(p["attributes"]["POSITION"])
        self.assertEqual(report["triangles_after"], 8)
        self.assertEqual(len(positions), 9)
        self.assertEqual(positions[:4], original)
        self.assertEqual(
            g.read(p["attributes"]["TEXCOORD_0"]), [v[:2] for v in positions]
        )
        self.assertTrue(
            all(v == (0.0, 0.0, 1.0) for v in g.read(p["attributes"]["NORMAL"]))
        )
        self.assertTrue(
            all(abs(v[2] - 0.1) < 1e-6 for v in g.read(p["targets"][0]["POSITION"]))
        )
        # Plane area and winding survive refinement; no cracks or flipped patches.
        indices = [r[0] for r in g.read(p["indices"])]
        area = 0
        for i in range(0, len(indices), 3):
            a, b, c = (positions[j] for j in indices[i : i + 3])
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            self.assertGreater(cross, 0)
            area += cross / 2
        self.assertAlmostEqual(area, 1.0)

    def test_shared_edge_blends_the_original_bone_weights(self):
        g, p = self.fixture()
        refine_nexo_face(g)
        positions = g.read(p["attributes"]["POSITION"])
        center = positions.index((0.5, 0.5, 0.0))
        joints = g.read(p["attributes"]["JOINTS_0"])[center]
        weights = g.read(p["attributes"]["WEIGHTS_0"])[center]
        self.assertEqual(
            {int(j): w for j, w in zip(joints, weights) if w}, {0: 0.5, 1: 0.5}
        )
        for row in g.read(p["attributes"]["WEIGHTS_0"]):
            self.assertAlmostEqual(sum(row), 1.0)

    def test_only_interior_edges_curve_and_source_vertices_do_not_drift(self):
        g, p = self.fixture()
        p["attributes"]["NORMAL"] = g.append(
            [(-0.6, 0.0, 0.8), (0.0, 0.0, 1.0), (0.6, 0.0, 0.8), (0.0, 0.0, 1.0)],
            "VEC3",
            5126,
        )
        before = g.read(p["attributes"]["POSITION"])
        refine_nexo_face(g)
        rows = g.read(p["attributes"]["POSITION"])
        self.assertEqual(rows[:4], before)
        center = next(
            v for v in rows[4:] if abs(v[0] - 0.5) < 1e-6 and abs(v[1] - 0.5) < 1e-6
        )
        self.assertGreater(center[2], 0)
        self.assertTrue(all(v[2] == 0 for v in rows[4:] if v != center))
