"""Tests for portable schema, reference guard and collision behavior (no COM)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collision_detector import detect_collisions
from layout import apply_auto_layout
from reference_reproduction_guard import enforce_reference_reproduction
from run_pipeline import reference_requested
from schema import Diagram


class CoreTests(unittest.TestCase):
    def test_examples_have_valid_layout_and_edges(self):
        for path in (ROOT / "examples").glob("*.json"):
            with self.subTest(example=path.name):
                diagram = apply_auto_layout(Diagram.model_validate(json.loads(path.read_text(encoding="utf-8"))))
                self.assertTrue(diagram.nodes)
                self.assertTrue(all(n.x is not None and n.y is not None for n in diagram.nodes))

    def test_unknown_edge_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            Diagram.model_validate({"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "missing"}]})

    def test_reference_intent_preserves_coordinates(self):
        raw, _ = enforce_reference_reproduction({"nodes": [{"id": "a", "x": 3.0, "y": 4.0}]}, "照着画")
        diagram = apply_auto_layout(Diagram.model_validate(raw))
        self.assertTrue(reference_requested(raw))
        self.assertFalse(raw["reference_locked"]["allow_free_layout"])
        self.assertEqual((diagram.nodes[0].x, diagram.nodes[0].y), (3.0, 4.0))

    def test_overlap_is_reported(self):
        diagram = Diagram.model_validate({"nodes": [
            {"id": "a", "x": 2, "y": 2, "width": 1, "height": 1},
            {"id": "b", "x": 2.1, "y": 2, "width": 1, "height": 1}]})
        self.assertTrue(any(i["type"] == "dense_region_collision" for i in detect_collisions(diagram)))

    def test_separated_nodes_pass(self):
        diagram = Diagram.model_validate({"nodes": [
            {"id": "a", "x": 2, "y": 2, "width": 1, "height": 1},
            {"id": "b", "x": 4, "y": 2, "width": 1, "height": 1}]})
        self.assertEqual(detect_collisions(diagram), [])


if __name__ == "__main__":
    unittest.main()
