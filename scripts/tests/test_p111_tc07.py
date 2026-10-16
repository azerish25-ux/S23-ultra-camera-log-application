"""Tests for TC-P111-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem.",
        "model": "layered",
        "subjectCoverage": 1.0,
        "subjectDefocus": 0.0,
        "foregroundDefocus": 4.0,
        "backgroundDefocus": 6.0,
        "leakage": 0.0,
        "energy": 1.0,
    }
    base.update(overrides)
    return base


class TCP11107(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))
        self.assertTrue(any("missing-background" in item for item in result["openQuestions"]))

    def test_layered_bokeh_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("leakage:0.0", result["preservedResults"])

    def test_uniform_background_blur_is_rejected(self):
        result = evaluate(payload(model="uniform-background"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("uniform-background-blur-without-coverage-model", result["rejectedClaims"])

    def test_leakage_through_an_opaque_subject_is_rejected(self):
        result = evaluate(payload(leakage=0.2))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("bokeh-leakage-through-opaque-subject", result["rejectedClaims"])

    def test_unnormalized_energy_is_rejected(self):
        result = evaluate(payload(energy=1.4, repeat="estimated-depth"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("energy-not-normalized", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(subjectCoverage=2.0))
