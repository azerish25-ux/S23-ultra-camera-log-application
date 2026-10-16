"""Tests for TC-P110-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat thin objects",
        "historyDepth": [0.2, 0.2, 1.5],
        "historyValid": [True, False, True],
        "currentDepth": [0.2, 1.6, 1.5],
        "fill": "current-evidence",
    }
    base.update(overrides)
    return base


class TCP11002(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_current_evidence_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("uncertainty" in item for item in result["reasons"]))

    def test_old_depth_fill_is_rejected(self):
        result = evaluate(payload(fill="old-depth"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("old-depth-fill-newly-visible", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p110-hair"
        result = evaluate(payload(evidenceId=evidence, repeat="hair"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
