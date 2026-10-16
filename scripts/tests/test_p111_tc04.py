"""Tests for TC-P111-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination.",
        "cut": True,
        "timestampsContinuous": True,
        "historyCarried": False,
    }
    base.update(overrides)
    return base


class TCP11104(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_cut_resets_history_even_when_timestamps_continue(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("cut:True", result["preservedResults"])
        self.assertIn("history_carried:False", result["preservedResults"])

    def test_continuous_timestamps_do_not_keep_history_across_a_cut(self):
        result = evaluate(payload(historyCarried=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("continuous-timestamps-preserve-history-across-cut", result["rejectedClaims"])
        self.assertIn("p111-evidence", result["preservedResults"])

    def test_same_shot_may_keep_history(self):
        result = evaluate(payload(cut=False, historyCarried=True, repeat="fades"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(cut="yes"))
