"""Tests for TC-P111-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat backlighting, crossing subjects, and different foreground-background contrast.",
        "mask": "partial-coverage",
        "coverage": [0.0, 0.4, 1.0],
        "haloRadius": 1.5,
        "haloLimit": 2.0,
    }
    base.update(overrides)
    return base


class TCP11105(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_partial_coverage_inside_the_halo_bound_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("fractional:1", result["preservedResults"])

    def test_dilated_binary_mask_is_rejected(self):
        result = evaluate(payload(mask="dilated-binary", coverage=[0.0, 1.0, 1.0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dilated-binary-person-mask", result["rejectedClaims"])

    def test_binary_samples_are_not_partial_coverage(self):
        result = evaluate(payload(coverage=[0.0, 1.0, 0.0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("binary-coverage-not-partial", result["rejectedClaims"])

    def test_halo_above_the_bound_is_rejected(self):
        result = evaluate(payload(haloRadius=3.0, repeat="backlighting"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("temporal-halo-exceeds-bound", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(coverage=[0.0, 1.4]))
