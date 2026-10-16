"""Tests for TC-P112-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p112-tc07",
        "repeat": "perfect-depth",
        "background_blur": [0.2, 0.8, 0.5, 1.1],
        "foreground_coverage": [1.0, 0.0, 0.25, 0.0],
        "leakage": 0.02,
        "leakage_limit": 0.05,
    }
    base.update(overrides)
    return base


class TCP11207(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("coverage_energy=") for item in result["preservedResults"]))

    def test_coverage_model_inside_leakage_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_uniform_blur_without_coverage_is_rejected(self):
        result = evaluate(payload(background_blur=[0.7, 0.7, 0.7, 0.7], foreground_coverage=[]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("uniform-background-blur-without-foreground-coverage", result["rejectedClaims"])

    def test_leakage_over_limit_is_rejected_and_evidence_remains(self):
        evidence = "p112-tc07-estimated"
        result = evaluate(payload(leakage=0.4, evidenceId=evidence, repeat="estimated-depth"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("bokeh-leakage-exceeds-declared-limit", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(foreground_coverage=[0.0, 1.2]))
