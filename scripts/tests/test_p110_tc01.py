"""Tests for TC-P110-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat translation",
        "previous": [1.0, 1.0, 0.25, 1.0, 1.0],
        "current": [1.0, 1.0, 1.0, 0.25, 1.0],
        "shift": 1,
        "blend": "reprojected",
    }
    base.update(overrides)
    return base


class TCP11001(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_reprojected_history_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_stationary_average_leaves_a_depth_trail(self):
        result = evaluate(payload(blend="stationary"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stationary-pixel-average-depth-trails", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p110-with"
        result = evaluate(payload(evidenceId=evidence, repeat="with rotation"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(shift=True))
