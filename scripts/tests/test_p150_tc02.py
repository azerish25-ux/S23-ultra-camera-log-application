"""Tests for TC-P150-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p150_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p150_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="timestamp pairing")
    base.update({"lineCoverage": 0.95, "mutantDetected": True})
    base.update(overrides)
    return base


class TCP15002(unittest.TestCase):
    def assert_contract(self, result, evidence="p150-signing-distribution"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P150-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_killed_mutants_are_recorded_despite_high_coverage(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["lineCoverage"], 0.95)
        self.assertTrue(result["preservedResults"][3]["mutantDetected"])
        self.assertEqual(_MODULE.CASE["name"], "Critical mutant survives")

    def test_high_coverage_without_detection_is_rejected(self):
        result = evaluate(payload(mutantDetected=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CRITICAL_MUTANT_SURVIVED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_low_coverage_still_rejects_a_survivor(self):
        result = evaluate(payload(lineCoverage=0.1, mutantDetected=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CRITICAL_MUTANT_SURVIVED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_inserted_uninstall_mutant_is_rejected_even_when_detected(self):
        result = evaluate(payload(recommends_uninstall=True, warns_footage_loss=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNINSTALL_WITHOUT_WARNING, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][3]["uninstallWithoutWarning"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p150-tc02-checkpoint"
        result = evaluate(payload(evidenceId=evidence, repeat="checkpoint identity"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(lineCoverage=1.2))
        with self.assertRaises(ValueError):
            evaluate(payload(lineCoverage=True))
