"""Tests for TC-P110-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat stationary backgrounds",
        "frames": [[0.30, 0.55, 0.70], [0.05, 0.55, 0.70]],
        "stationary": [1],
        "normalization": "aligned",
    }
    base.update(overrides)
    return base


class TCP11003(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_aligned_scale_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_honest_reset_is_recorded(self):
        result = evaluate(payload(normalization="reset"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_independent_minmax_pumps_stationary_background(self):
        result = evaluate(payload(normalization="independent-minmax"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-minmax-normalization-per-frame", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
