"""Tests for TC-P115-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p115_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p115_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p115-blur",
        "existingBlur": "short-exposure",
        "claimExactConversion": False,
        "additionalProcessing": "qualified-additional",
        "repeat": "short-exposure",
    }
    base.update(overrides)
    return base


class TCP11502(unittest.TestCase):
    def assert_contract(self, result, evidence="p115-blur"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P115-02")
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
                evidenceId="p115-long",
                existingBlur="long-exposure",
                additionalProcessing="identified-unreconstructable",
                repeat="long-exposure",
            )
        )
        self.assert_contract(recorded, "p115-long")
        self.assertEqual(recorded["decision"], "recorded")

    def test_undersampled_exact_claim_is_rejected(self):
        result = evaluate(
            payload(
                existingBlur="undersampled-thin",
                claimExactConversion=True,
                additionalProcessing="identified-unreconstructable",
                repeat="undersampled-thin",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exact-arbitrary-shutter-conversion", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(existingBlur="clean"))
