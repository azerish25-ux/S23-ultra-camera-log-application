"""Tests for TC-P115-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p115_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p115_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SHIFT = [[1.5, -0.25], [2.0, -0.5]]
STILL = [[0.0, 0.0], [0.0, 0.0]]


def payload(**overrides):
    base = {
        "evidenceId": "p115-stab",
        "rgbTransform": SHIFT,
        "depthTransform": SHIFT,
        "maskTransform": SHIFT,
        "validRegionUpdated": True,
        "fovUpdated": True,
        "repeat": "crop",
    }
    base.update(overrides)
    return base


class TCP11505(unittest.TestCase):
    def assert_contract(self, result, evidence="p115-stab"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P115-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Stabilization-depth misalignment")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Stabilizing color alone while leaving masks unchanged must fail.",
        )
        self.assertIn("portrait rotation", _MODULE.REPEAT)

    def test_shared_transform_is_recorded(self):
        result = evaluate(payload(repeat="portrait-rotation"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["mask"], SHIFT)

    def test_color_only_stabilization_keeps_the_unchanged_mask(self):
        result = evaluate(payload(maskTransform=STILL, depthTransform=STILL, repeat="combined-motion"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("color-stabilized-mask-unchanged", result["rejectedClaims"])
        self.assertIn("depth-not-transformed", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["mask"], STILL)
        self.assertNotEqual(result["preservedResults"][1]["mask"], SHIFT)

    def test_missing_valid_region_is_rejected_and_identity_is_recorded(self):
        rejected = evaluate(payload(validRegionUpdated=False, fovUpdated=False))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("valid-region-not-updated", rejected["rejectedClaims"])
        self.assertIn("fov-not-updated", rejected["rejectedClaims"])
        recorded = evaluate(
            payload(
                evidenceId="p115-identity",
                rgbTransform=STILL,
                depthTransform=STILL,
                maskTransform=STILL,
                validRegionUpdated=False,
                fovUpdated=False,
            )
        )
        self.assert_contract(recorded, "p115-identity")
        self.assertEqual(recorded["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(depthTransform=[[1.5, -0.25]]))
