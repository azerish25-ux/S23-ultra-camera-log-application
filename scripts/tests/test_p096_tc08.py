"""Tests for TC-P096-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p096_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p096_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p096-evidence",
        "repeat": "Repeat",
        "applyNegative": False,
        "applyMutant": False,
    }
    base.update(overrides)
    return base


class TCP09608(unittest.TestCase):
    def assert_contract(self, result, evidence="p096-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P096-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(applyNegative=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("format-selector-implemented-solely-color-lut", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="standard"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("format-selector-implemented-solely-color-lut", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p096-standard"
        result = evaluate(payload(evidenceId=evidence, repeat="standard"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
