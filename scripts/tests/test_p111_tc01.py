"""Tests for TC-P111-01."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
reproject = _MODULE.reproject

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat translation, rotation, scale change, and camera motion.",
        "history": [{"x": 10.0, "y": 4.0, "depth": 2.0}],
        "motion": {"dx": 3.0, "dy": -1.0, "scale": 2.0, "rotation_deg": 90.0},
        "blend": "reprojected",
    }
    base.update(overrides)
    return base


class TCP11101(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_reprojected_history_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        warped = reproject({"x": 10.0, "y": 4.0, "depth": 2.0}, payload()["motion"])
        self.assertNotEqual((warped["x"], warped["y"]), (10.0, 4.0))
        self.assertTrue(any(str(warped["x"])[:6] in item or f"{warped['x']:.6g}" in item for item in result["reasons"]))
        self.assertIn("warped-count:1", result["preservedResults"])

    def test_stationary_pixel_average_is_rejected(self):
        result = evaluate(payload(blend="stationary-pixel"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stationary-pixel-average-depth-trails", result["rejectedClaims"])
        self.assertIn("p111-evidence", result["preservedResults"])

    def test_identity_motion_can_stay_on_stationary_pixels(self):
        motion = {"dx": 0.0, "dy": 0.0, "scale": 1.0, "rotation_deg": 0.0}
        result = evaluate(payload(blend="stationary-pixel", motion=motion, repeat="rotation"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        warped = reproject({"x": 10.0, "y": 4.0, "depth": 2.0}, motion)
        self.assertTrue(math.isclose(warped["x"], 10.0))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        result = evaluate(payload(evidenceId="p111-translation", repeat="translation"))
        self.assert_contract(result, "p111-translation")
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(history=[]))
