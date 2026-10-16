"""Tests for TC-P117-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc02.py",
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
        "evidenceId": "p117-blur",
        "repeat": "short-exposure",
        "sources": [
            {"id": "short", "blurSeconds": 0.125},
            {"id": "long", "blurSeconds": 0.25},
        ],
        "targetExposureSeconds": 0.5,
        "claimExactConversion": False,
        "thinMotionUndersampled": False,
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11702(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-blur"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Existing blur ambiguity")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Claiming exact arbitrary shutter conversion from any source must fail.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat short exposure, long exposure, and undersampled thin motion.",
        )

    def test_additional_blur_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(_MODULE.additional_blur(0.5, 0.125), 0.375)
        self.assertEqual(_MODULE.additional_blur(0.5, 0.25), 0.25)
        self.assertIn("additionalBlur short=0.375 long=0.25", result["preservedResults"])

    def test_exact_conversion_claim_is_rejected(self):
        result = evaluate(payload(claimExactConversion=True, repeat="long-exposure"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("additionalBlur short=0.375 long=0.25", result["preservedResults"])

    def test_shorter_target_cannot_remove_existing_blur(self):
        result = evaluate(payload(targetExposureSeconds=0.125, repeat="long-exposure"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CANNOT_RECONSTRUCT, result["rejectedClaims"])
        self.assertIsNone(_MODULE.additional_blur(0.125, 0.25))
        self.assertIn("long=unreconstructable", blob(result))

    def test_undersampled_thin_motion_is_rejected(self):
        result = evaluate(payload(thinMotionUndersampled=True, repeat="undersampled-thin-motion"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDERSAMPLED, result["rejectedClaims"])

    def test_full_frame_translation_is_rejected_with_the_blur_math(self):
        geo = geometry()
        geo["crop"] = {"x": 0.0, "y": 0.0, "width": 4.0, "height": 2.0}
        geo["stabilized"] = {"lensId": "s23-main", "timestamp": 0.0, "aspect": 2.0}
        geo["reportedHorizontalFovDegrees"] = _MODULE._CORE.expected_horizontal_fov(4, 90, 0, 4)
        result = evaluate(payload(geometry=geo))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("full-frame-hides-lost-borders", result["rejectedClaims"])
        self.assertIn("p117-blur", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
