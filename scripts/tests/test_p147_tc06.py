"""Tests for TC-P147-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p147_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p147_tc06.py",
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


def replace_import(import_id, **overrides):
    rows = _GATE.fixture_imports()
    for row in rows:
        if row["id"] == import_id:
            row.update(overrides)
    return rows


class TCP14706(unittest.TestCase):
    def assert_contract(self, result, evidence="p147-secure-import"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P147-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_explicit_migration_preserves_private_media(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_refusal_that_keeps_counts_is_recorded(self):
        result = evaluate(payload(migration="refused"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_silent_uninstall_is_rejected(self):
        result = evaluate(payload(migration="silent-uninstall", signed=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.DESTRUCTIVE_UPDATE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_dropping_sources_is_rejected(self):
        result = evaluate(payload(sourcesAfter=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DESTRUCTIVE_UPDATE, result["rejectedClaims"])

    def test_magic_disagreement_is_rejected_inside_the_case(self):
        result = evaluate(payload(imports=replace_import("lut-cube", magic="PK", trust_extension=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.TRUSTED_EXTENSION, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p147-tc06-rollback"
        result = evaluate(payload(evidenceId=evidence, repeat="rollback limits"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(migration="delete"))
        with self.assertRaises(ValueError):
            evaluate(payload(sourcesBefore=-1))
