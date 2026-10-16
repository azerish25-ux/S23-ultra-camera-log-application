"""Tests for TC-P103-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p103_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p103-evidence",
        "repeat": "Repeat",
        "applyNegative": False,
        "applyMutant": False,
        "loaded": True,
        "depthError": 0.02,
        "boundaryError": 0.03,
        "depthTolerance": 0.05,
        "boundaryTolerance": 0.05,
        "numericallyQualifiedClaim": False,
    }
    base.update(overrides)
    return base


class TCP10303(unittest.TestCase):
    def assert_contract(self, result, evidence="p103-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P103-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(applyNegative=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("model-merely-runs-numerically-qualified", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="hair"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("model-merely-runs-numerically-qualified", result["rejectedClaims"])

    def test_loaded_model_outside_tolerance_is_not_numerically_qualified(self):
        result = evaluate(payload(depthError=0.5, boundaryError=0.4, numericallyQualifiedClaim=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("model-merely-runs-numerically-qualified", result["rejectedClaims"])

    def test_over_tolerance_without_qualification_claim_stays_experimental(self):
        result = evaluate(payload(depthError=0.4, boundaryError=0.4, numericallyQualifiedClaim=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("experimental" in item for item in result["reasons"]))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p103-hair"
        result = evaluate(payload(evidenceId=evidence, repeat="hair"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
