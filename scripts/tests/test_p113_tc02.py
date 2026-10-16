"""Tests for TC-P113-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "short-exposure",
        "sourceBlurSeconds": "1/96",
        "shutterAngleDegrees": 180,
        "fps": 24,
        "claimExactConversion": False,
        "syntheticIntegration": False,
        "sensorConfirmed": False,
        "measurementId": None,
        "sourceCadenceFps": 24,
    }
    base.update(overrides)
    return base


class TCP11302(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_clean_short_exposure_adds_only_qualified_blur(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        self.assertIn("additional exposure 1/96 s", result["reasons"])
        self.assertIn("exact conversion is not claimed", " ".join(result["reasons"]))

    def test_exact_conversion_and_existing_long_blur_are_rejected(self):
        exact = evaluate(payload(claimExactConversion=True))
        self.assert_contract(exact)
        self.assertEqual(exact["decision"], "rejected")
        self.assertIn("exact-arbitrary-shutter-conversion", exact["rejectedClaims"])
        long_blur = evaluate(payload(repeat="long-exposure", sourceBlurSeconds="1/24"))
        self.assertEqual(long_blur["decision"], "rejected")
        self.assertIn("cannot-faithfully-remove-blur", long_blur["rejectedClaims"])
        thin = evaluate(payload(repeat="undersampled-thin-motion"))
        self.assertEqual(thin["decision"], "rejected")
        self.assertIn("cannot-faithfully-reconstruct", thin["rejectedClaims"])

    def test_second_evidence_id_is_preserved(self):
        result = evaluate(payload(evidenceId="p113-blur", repeat="short-exposure"))
        self.assert_contract(result, "p113-blur")
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceBlurSeconds=0))
        with self.assertRaises(ValueError):
            evaluate(payload(fps=-1))
