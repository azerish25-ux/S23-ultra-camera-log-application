"""Tests for TC-P113-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
ROTATION = [0, -1, 1, 0]
IDENTITY = [1, 0, 0, 1]


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "crop-change",
        "rgbTransform": list(ROTATION),
        "depthTransform": list(ROTATION),
        "maskTransform": list(ROTATION),
        "validRegionUpdated": True,
        "fovUpdated": True,
        "cropChanged": True,
        "shutterAngleDegrees": 180,
        "fps": 24,
        "sensorConfirmed": False,
        "measurementId": None,
        "syntheticIntegration": False,
    }
    base.update(overrides)
    return base


class TCP11305(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_shared_transform_updates_valid_region_and_fov(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("valid-region-updated:true", result["preservedResults"])
        self.assertIn("fov-updated:true", result["preservedResults"])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        portrait = evaluate(payload(repeat="portrait-rotation"))
        self.assertEqual(portrait["decision"], "recorded")

    def test_color_only_stabilization_is_rejected(self):
        result = evaluate(payload(
            repeat="combined-motion",
            maskTransform=list(IDENTITY),
            depthTransform=list(IDENTITY),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stabilized-color-left-masks-unchanged", result["rejectedClaims"])

    def test_stale_valid_region_is_rejected(self):
        result = evaluate(payload(validRegionUpdated=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("valid-region-or-fov-stale", result["rejectedClaims"])
        self.assertIn("p113-evidence", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(rgbTransform=[1, 0]))
        with self.assertRaises(ValueError):
            evaluate(payload(shutterAngleDegrees=0))
