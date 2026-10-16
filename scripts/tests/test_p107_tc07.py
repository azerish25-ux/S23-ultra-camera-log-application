"""Tests for TC-P107-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "perfect-depth",
        "uniform_background_blur": False,
        "foreground_coverage_model": True,
        "subject_coverage": 1.0,
        "background_energy": 0.7,
        "foreground_energy": 0.3,
        "missing_background_declared": False,
        "subject_in_front": True,
    }
    base.update(overrides)
    return base


class TCP10707(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_layered_normalized_energy_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("composite_energy=0.3", result["preservedResults"])

    def test_uniform_background_blur_without_coverage_is_rejected(self):
        result = evaluate(payload(uniform_background_blur=True, foreground_coverage_model=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("uniform-background-blur", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_undeclared_energy_gap_is_rejected(self):
        evidence = "p107-estimated"
        result = evaluate(payload(evidenceId=evidence, background_energy=0.2, foreground_energy=0.2))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("energy-not-normalized", result["rejectedClaims"])

    def test_declared_missing_background_stays_recorded(self):
        result = evaluate(payload(background_energy=0.2, foreground_energy=0.2, missing_background_declared=True))
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("missing-background" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
