"""Tests for TC-P110-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat hard cuts",
        "cut": True,
        "timestampsContinuous": True,
        "history": [0.2, 0.4, 0.6],
        "current": [0.9, 0.1, 0.0],
        "policy": "reset",
    }
    base.update(overrides)
    return base


class TCP11004(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_reset_at_cut_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_continuous_timestamps_do_not_keep_history_across_a_cut(self):
        result = evaluate(payload(policy="preserve"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("timestamps-alone-preserve-temporal-state-across-cut", result["rejectedClaims"])
        self.assertTrue(any("continuous timestamps" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
