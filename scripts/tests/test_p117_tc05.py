"""Tests for TC-P117-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def geometry(**overrides):
    value = _MODULE._CORE.recorded_geometry()
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p117-align",
        "repeat": "crop-changes",
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11705(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-align"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Stabilization-depth misalignment")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Apply a changing stabilization transform to RGB while depth begins in source coordinates.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Transform all relevant geometry consistently and update valid region and field-of-view evidence.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Stabilizing color alone while leaving masks unchanged must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat crop changes, portrait rotation, and combined camera and subject motion.",
        )

    def test_shared_translation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))
        self.assertIn(
            "sample[0] layer=depth output=(1,0) source=(0,0) status=known inCrop=yes depth=0",
            result["preservedResults"],
        )
        self.assertIn("validRegion=(0,0)-(3,2)", blob(result))

    def test_unchanged_mask_is_rejected(self):
        geo = geometry()
        geo["layers"] = {
            "rgb": {"dx": 1.0, "dy": 0.0},
            "depth": {"dx": 1.0, "dy": 0.0},
            "mask": {"dx": 0.0, "dy": 0.0},
        }
        result = evaluate(payload(geometry=geo))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MASK_UNTRANSFORMED, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_depth_left_in_source_coordinates_is_rejected(self):
        geo = geometry()
        geo["layers"] = {
            "rgb": {"dx": 1.0, "dy": 0.0},
            "depth": {"dx": 0.0, "dy": 0.0},
            "mask": {"dx": 1.0, "dy": 0.0},
        }
        result = evaluate(payload(geometry=geo, repeat="combined-camera-and-subject-motion"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.DEPTH_LEFT_IN_SOURCE, result["rejectedClaims"])
        self.assertIn(
            "sample[0] layer=depth output=(1,0) source=(1,0) status=known inCrop=yes depth=1",
            result["preservedResults"],
        )

    def test_stale_fov_is_rejected(self):
        geo = geometry(reportedHorizontalFovDegrees=90.0)
        result = evaluate(payload(geometry=geo, repeat="portrait-rotation"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("fov-does-not-reflect-crop", result["rejectedClaims"])

    def test_full_frame_claim_is_rejected(self):
        geo = geometry()
        geo["crop"] = {"x": 0.0, "y": 0.0, "width": 4.0, "height": 2.0}
        geo["stabilized"] = {"lensId": "s23-main", "timestamp": 0.0, "aspect": 2.0}
        geo["reportedHorizontalFovDegrees"] = _MODULE._CORE.expected_horizontal_fov(4, 90, 0, 4)
        result = evaluate(payload(geometry=geo))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("full-frame-hides-lost-borders", result["rejectedClaims"])
        self.assertIn("cropCoverage=8/8=1", blob(result))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p117-align-crop"
        result = evaluate(payload(evidenceId=evidence, repeat="crop-changes"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
