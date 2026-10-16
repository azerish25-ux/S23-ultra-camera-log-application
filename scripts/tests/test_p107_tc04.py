"""Tests for TC-P107-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "hard-cut",
        "scene_cut": True,
        "timestamps_continuous": True,
        "history_reset": True,
        "leaked_depth": False,
        "leaked_color": False,
    }
    base.update(overrides)
    return base


class TCP10704(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_reset_cut_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("contamination=0", result["preservedResults"])

    def test_continuous_timestamps_do_not_preserve_a_cut(self):
        result = evaluate(payload(history_reset=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("continuous-timestamps-preserve-state", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_leaked_color_is_rejected(self):
        evidence = "p107-fade"
        result = evaluate(payload(evidenceId=evidence, leaked_color=True, timestamps_continuous=False))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("previous-image-leak", result["rejectedClaims"])

    def test_no_cut_without_leakage_is_recorded(self):
        result = evaluate(payload(scene_cut=False, history_reset=False, timestamps_continuous=True))
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
