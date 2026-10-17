"""Tests for TC-P146-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p146_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p146_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def catalogue_with(mutant_id: str, **overrides):
    catalogue = _GATE.fixture_catalogue()
    for mutant in catalogue:
        if mutant["id"] == mutant_id:
            mutant.update(overrides)
    return catalogue


def payload(**overrides):
    base = _GATE.core_payload(repeat="timestamp pairing")
    base.update({"lineCoverage": 0.95})
    base.update(overrides)
    return base


class TCP14602(unittest.TestCase):
    def assert_contract(self, result, evidence="p146-property-mutation"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P146-02")
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
        self.assertEqual(result["preservedResults"][3]["survivedMutants"], [])
        self.assertEqual(_MODULE.CASE["name"], "Critical mutant survives")

    def test_high_coverage_without_detection_is_rejected(self):
        result = evaluate(payload(catalogue=catalogue_with("range-confusion", detected=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.MUTANT_NOT_DETECTED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("range-confusion", result["preservedResults"][1]["survivedMutants"])

    def test_low_coverage_still_rejects_a_survivor(self):
        result = evaluate(payload(
            lineCoverage=0.1,
            catalogue=catalogue_with("timestamp-reuse", detected=False),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.MUTANT_NOT_DETECTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_happy_path_catalogue_is_rejected(self):
        result = evaluate(payload(catalogue=_GATE.happy_path_catalogue(), lineCoverage=0.99))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.HAPPY_PATH_ONLY, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p146-tc02-checkpoint"
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
