"""Tests for TC-P110-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat blinded presentation",
        "scores": [0.9, 0.95, 0.2, 0.92],
        "catastrophic": [False, False, True, False],
        "policy": "limit-release",
    }
    base.update(overrides)
    return base


class TCP11008(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_limited_release_records_catastrophic_frames(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("catastrophic frames 2" in item for item in result["reasons"]))

    def test_favorable_mean_cannot_hide_severe_frames(self):
        result = evaluate(payload(policy="mean-only"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mean-score-hides-severe-boundary-failures", result["rejectedClaims"])

    def test_clean_mean_is_recorded(self):
        result = evaluate(payload(policy="mean-only", catastrophic=[False, False, False, False]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
