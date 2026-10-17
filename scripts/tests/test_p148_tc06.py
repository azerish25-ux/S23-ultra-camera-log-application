"""Tests for TC-P148-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p148_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p148_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="interrupted migration")
    base.update({
        "signed": True,
        "migration": "explicit",
        "sourcesBefore": 2,
        "profilesBefore": 1,
        "recoveryBefore": 1,
        "sourcesAfter": 2,
        "profilesAfter": 1,
        "recoveryAfter": 1,
    })
    base.update(overrides)
    return base


class TCP14806(unittest.TestCase):
    def assert_contract(self, result, evidence="p148-offline-privacy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P148-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_explicit_preservation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["migration"], "explicit")
        self.assertEqual(_MODULE.CASE["name"], "Update threatens private media")

    def test_refusing_migration_without_loss_is_recorded(self):
        result = evaluate(payload(migration="refused"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_silent_uninstall_is_rejected(self):
        result = evaluate(payload(signed=False, migration="silent-uninstall", sourcesAfter=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.DESTRUCTIVE_UPDATE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_dropped_recovery_data_is_rejected(self):
        result = evaluate(payload(recoveryAfter=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DESTRUCTIVE_UPDATE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p148-tc06-rollback"
        result = evaluate(payload(evidenceId=evidence, repeat="rollback limits"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(migration="magic"))
        with self.assertRaises(ValueError):
            evaluate(payload(sourcesBefore=-1))
