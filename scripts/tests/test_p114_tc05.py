"""Tests for TC-P114-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
TRANSFORM = [1.0, 0.0, 2.0, 0.0, 1.0, 3.0]


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "crop changes",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [{"origin": "captured", "weight": 1.0}],
        "rgb_transform": list(TRANSFORM),
        "depth_transform": list(TRANSFORM),
        "mask_transform": list(TRANSFORM),
        "valid_region_updated": True,
        "field_of_view_updated": True,
    }
    base.update(overrides)
    return base


class TCP11405(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_shared_transform_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_color_stabilized_without_masks_is_rejected(self):
        result = evaluate(payload(mask_transform=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0], repeat="portrait rotation"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stabilizing-color-alone-leaving-masks-unchanged", result["rejectedClaims"])

    def test_depth_left_behind_or_stale_crop_is_rejected(self):
        depth = evaluate(payload(depth_transform=[0.0, 1.0, 0.0, 1.0, 0.0, 0.0]))
        self.assertIn("depth-not-transformed-with-color", depth["rejectedClaims"])
        region = evaluate(payload(valid_region_updated=False, field_of_view_updated=False, repeat="combined camera and subject motion"))
        self.assertIn("valid-region-or-fov-not-updated", region["rejectedClaims"])
        self.assertIn("p114-evidence", region["preservedResults"])

    def test_scope_rules_still_apply(self):
        hidden = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0}],
            contains_estimated=True,
            disclosed=False,
        ))
        self.assertIn("hidden-hallucination", hidden["rejectedClaims"])
        weights = evaluate(payload(frames=[{"origin": "captured", "weight": 2.0}]))
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])
        missing = evaluate(payload(shutter_angle_degrees=None, fps=None))
        self.assertIn("missing-shutter-angle", missing["rejectedClaims"])
        self.assertIn("missing-fps", missing["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-rotation"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait rotation"))
        self.assert_contract(result, evidence)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(rgb_transform=[]))
