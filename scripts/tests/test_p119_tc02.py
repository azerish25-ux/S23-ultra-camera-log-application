"""Tests for TC-P119-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p119_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p119_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _guidance(**overrides):
    statement = {
        "text": "keep the measured shutter and fps",
        "limitId": "mode-24",
        "recommendsFps": None,
        "recommendsShutter": None,
        "observedMotionPx": 1.0,
        "claimsStableMotion": True,
        "promises": [],
    }
    statement.update(overrides)
    return [statement]


def payload(**overrides):
    base = {
        "evidenceId": "p119-blur",
        "existingBlur": "short-exposure",
        "claimExactConversion": False,
        "additionalProcessing": "qualified-additional",
        "repeat": "short-exposure",
        "selectedLimitId": "mode-24",
        "measuredLimits": [
            {
                "id": "mode-24",
                "fps": 24.0,
                "shutter_angle": 180.0,
                "max_stable_motion_px": 8.0,
                "mode_available": True,
            }
        ],
        "guidance": _guidance(),
    }
    base.update(overrides)
    return base


class TCP11902(unittest.TestCase):
    def assert_contract(self, result, evidence="p119-blur"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P119-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Existing blur ambiguity")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Claiming exact arbitrary shutter conversion from any source must fail.",
        )
        self.assertIn("undersampled thin motion", _MODULE.REPEAT)

    def test_short_exposure_qualified_addition_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_exact_conversion_is_rejected(self):
        result = evaluate(payload(claimExactConversion=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exact-arbitrary-shutter-conversion", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("exact:true", result["preservedResults"])

    def test_long_exposure_must_be_identified(self):
        rejected = evaluate(
            payload(existingBlur="long-exposure", additionalProcessing="qualified-additional", repeat="long-exposure")
        )
        self.assert_contract(rejected)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("unfaithful-reconstruction", rejected["rejectedClaims"])
        recorded = evaluate(
            payload(
                evidenceId="p119-long",
                existingBlur="long-exposure",
                additionalProcessing="identified-unreconstructable",
                repeat="long-exposure",
            )
        )
        self.assert_contract(recorded, "p119-long")
        self.assertEqual(recorded["decision"], "recorded")

    def test_film_stock_promise_is_rejected_even_when_blur_is_qualified(self):
        result = evaluate(payload(guidance=_guidance(promises=["film-stock fidelity"])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("film-stock-fidelity", result["rejectedClaims"])
        self.assertIn("blur:short-exposure", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(existingBlur="none"))
