"""Tests for TC-P147-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p147_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p147_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="timestamp pairing")
    base.update({
        "lineCoverage": 0.95,
        "killedIds": list(_GATE.CRITICAL_CORPUS_IDS),
    })
    base.update(overrides)
    return base


class TCP14702(unittest.TestCase):
    def assert_contract(self, result, evidence="p147-secure-import"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P147-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_killed_import_mutants_are_recorded_despite_high_coverage(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["lineCoverage"], 0.95)
        self.assertEqual(result["preservedResults"][3]["survivedMutants"], [])
        self.assertEqual(_MODULE.CASE["name"], "Critical mutant survives")

    def test_high_coverage_without_detection_is_rejected(self):
        killed = [item for item in _GATE.CRITICAL_CORPUS_IDS if item != "trust-extension-unvalidated-header"]
        result = evaluate(payload(killedIds=killed))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT_NOT_DETECTED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("trust-extension-unvalidated-header", result["preservedResults"][3]["survivedMutants"])

    def test_low_coverage_still_rejects_a_survivor(self):
        killed = [item for item in _GATE.CRITICAL_CORPUS_IDS if item != "archive-traversal"]
        result = evaluate(payload(lineCoverage=0.1, killedIds=killed))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_NOT_DETECTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p147-tc02-checkpoint"
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
