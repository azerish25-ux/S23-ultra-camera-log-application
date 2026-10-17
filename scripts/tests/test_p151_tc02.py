"""Tests for TC-P151-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p151_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p151_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def mutants(**overrides_for):
    rows = [
        {"id": "timestamp-pairing", "critical": True, "expected_detection": True, "detected": True},
        {"id": "source-retention", "critical": True, "expected_detection": True, "detected": True},
        {"id": "range-signalling", "critical": True, "expected_detection": True, "detected": True},
        {"id": "checkpoint-identity", "critical": True, "expected_detection": True, "detected": True},
    ]
    if overrides_for:
        mutant_id, fields = next(iter(overrides_for.items()))
        for row in rows:
            if row["id"] == mutant_id:
                row.update(fields)
    return rows


def payload(**overrides):
    base = _GATE.core_payload(repeat="timestamp pairing")
    base.update({"lineCoverage": 0.95, "mutants": mutants()})
    base.update(overrides)
    return base


class TCP15102(unittest.TestCase):
    def assert_contract(self, result, evidence="p151-release-notes"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P151-02")
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
        result = evaluate(payload(mutants=mutants(**{"range-signalling": {"detected": False}})))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT_SURVIVED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("range-signalling", result["preservedResults"][3]["survivedMutants"])

    def test_low_coverage_still_rejects_a_survivor(self):
        result = evaluate(payload(
            lineCoverage=0.1,
            mutants=mutants(**{"timestamp-pairing": {"detected": False}}),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT_SURVIVED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_null_evidence_claim_in_implemented_features_is_rejected(self):
        claims = _GATE.fixture_claims() + [{
            "claim_id": "unmeasured-gate",
            "badge": "unavailable",
            "evidence_id": None,
            "limit": "not shipped",
        }]
        result = evaluate(payload(claims=claims, implementedFeatures=["sdr-recording", "unmeasured-gate"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.NULL_EVIDENCE_IMPLEMENTED, result["rejectedClaims"])
        self.assertIn(_GATE.UNAVAILABLE_SHIPPED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p151-tc02-checkpoint"
        result = evaluate(payload(evidenceId=evidence, repeat="checkpoint identity"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(lineCoverage=2))
        with self.assertRaises(ValueError):
            evaluate(payload(mutants=[]))
