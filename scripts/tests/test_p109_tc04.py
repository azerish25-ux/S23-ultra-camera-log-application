"""Tests for TC-P109-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "hard cuts",
        "sceneCut": True,
        "timestampsContinuous": True,
        "historyRetained": False,
    }
    base.update(overrides)
    return base


class TCP10904(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-04")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_cut_resets_history_and_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_continuous_timestamps_keep_history_and_evidence_remains(self):
        result = evaluate(payload(historyRetained=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("continuous-timestamps-preserve-state-across-cut", result["rejectedClaims"])

    def test_mutant_history_across_cut_is_rejected(self):
        result = evaluate(payload(historyRetained=True, timestampsContinuous=False, repeat="fades"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("continuous-timestamps-preserve-state-across-cut", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p109-pan"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="rapid camera pans",
            sceneCut=False,
            historyRetained=True,
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
