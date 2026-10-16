"""Tests for TC-P120-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SCALE = 1.25


def transform(**overrides):
    value = {"scale": SCALE, "rotationRadians": 0.1, "tx": 0.2, "ty": -0.3}
    value.update(overrides)
    return value


def honest_report(**overrides):
    value = {
        "shutter_angle": 180.0,
        "fps": 24.0,
        "exposure_seconds": (180.0 / 360.0) / 24.0,
        "interpolation_fraction": 0.0,
        "estimated_disclosed": False,
        "stabilization_crop_fraction": 1.0 - (1.0 / (SCALE * SCALE)),
        "rolling_shutter_readout": "unknown",
        "correction_applied": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p120-evidence",
        "repeat": "Repeat",
        "combinationPassed": True,
        "report": honest_report(),
        "rgbTransform": transform(),
        "depthTransform": transform(),
        "maskTransform": transform(),
        "sourceFovDegrees": 50.0,
        "reportedFovDegrees": 50.0 / SCALE,
        "sourceValidArea": 1.0,
        "reportedValidArea": 1.0 / (SCALE * SCALE),
    }
    base.update(overrides)
    return base


class TCP12005(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_shared_transform_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("shared stabilization transform" in item for item in result["reasons"]))

    def test_unchanged_mask_is_rejected(self):
        result = evaluate(payload(maskTransform=transform(scale=1.0)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_depth_left_in_source_coordinates_is_rejected(self):
        result = evaluate(payload(depthTransform=transform(tx=0.0)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DEPTH_TOKEN, result["rejectedClaims"])
        self.assertIn("defectOrigin=depth", result["reasons"])

    def test_fov_or_crop_mismatch_is_rejected(self):
        result = evaluate(payload(reportedFovDegrees=50.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOV_TOKEN, result["rejectedClaims"])

    def test_spot_check_cannot_replace_the_geometry_report(self):
        result = evaluate(payload(combinationPassed=True, report={"shutter_angle": 180.0}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("shutter-only-spot-check-claimed-combination-passed", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait rotation"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
