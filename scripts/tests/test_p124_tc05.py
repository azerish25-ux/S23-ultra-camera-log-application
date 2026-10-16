"""Tests for TC-P124-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "phase": "chunk-assembly",
        "remainingBytes": 500,
        "intermediateBytes": 200,
        "finalOutputBytes": 100,
        "budgetedBytes": 300,
        "sourcePreserved": True,
        "recoverableArtifacts": True,
        "action": "continue",
    }
    base.update(overrides)
    return base


class TCP12405(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("requiredBytes=300", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_budget_covering_intermediates_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_budgeting_only_final_bytes_is_rejected(self):
        result = evaluate(payload(budgetedBytes=100, remainingBytes=1000))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BUDGET_FINAL_ONLY, result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_pause_before_source_loss_is_recorded(self):
        result = evaluate(payload(remainingBytes=50, action="pause"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("pause before source loss", result["reasons"])

    def test_source_loss_and_continued_work_are_rejected(self):
        result = evaluate(payload(remainingBytes=50, sourcePreserved=False, recoverableArtifacts=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SOURCE_LOSS, result["rejectedClaims"])
        self.assertIn(_MODULE.NOT_RECOVERABLE, result["rejectedClaims"])
        self.assertIn(_MODULE.CONTINUED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-gallery"
        result = evaluate(payload(evidenceId=evidence, repeat="gallery", phase="gallery-publication"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
