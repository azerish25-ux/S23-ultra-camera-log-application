"""Tests for TC-P152-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p152_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p152_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def mutants(**overrides_for):
    rows = [
        {"id": "timestamp-pairing", "critical": True, "detected": True},
        {"id": "source-retention", "critical": True, "detected": True},
        {"id": "range-signalling", "critical": True, "detected": True},
        {"id": "checkpoint-identity", "critical": True, "detected": True},
    ]
    for row in rows:
        if row["id"] in overrides_for:
            row.update(overrides_for[row["id"]])
    return rows


def payload(**overrides):
    base = _GATE.core_payload(repeat="timestamp pairing")
    base.update({"lineCoverage": 0.95, "mutants": mutants()})
    base.update(overrides)
    return base


class TCP15202(unittest.TestCase):
    def assert_contract(self, result, evidence="p152-production-readiness"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P152-02")
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
        result = evaluate(payload(mutants=mutants(**{"source-retention": {"detected": False}})))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SURVIVOR, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("source-retention", result["preservedResults"][3]["survivedMutants"])

    def test_low_coverage_still_rejects_a_survivor(self):
        result = evaluate(payload(
            lineCoverage=0.1,
            mutants=mutants(**{"timestamp-pairing": {"detected": False}}),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SURVIVOR, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_data_loss_waiver_is_rejected_even_when_mutants_are_killed(self):
        risks = _GATE.replace_risk("staging-copy-deleted", status="accepted", reason="looks_convincing")
        result = evaluate(payload(risks=risks, release_decision="hold"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DATA_LOSS_WAIVER_REJECTED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][3]["survivedMutants"], [])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p152-tc02-checkpoint"
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
        with self.assertRaises(ValueError):
            evaluate(payload(mutants=[]))
