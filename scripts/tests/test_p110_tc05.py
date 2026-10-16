"""Tests for TC-P110-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat backlighting",
        "coverage": [0.0, 0.35, 1.0, 0.0],
        "mask": "partial",
    }
    base.update(overrides)
    return base


class TCP11005(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_partial_coverage_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_dilated_binary_mask_is_rejected(self):
        result = evaluate(payload(mask="dilated-binary"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dilated-binary-person-mask", result["rejectedClaims"])

    def test_unbounded_halo_is_rejected(self):
        result = evaluate(payload(coverage=[0.2, 0.2, 0.2, 0.2, 0.2]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unbounded-temporal-halo", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(coverage=[0.0, 1.4]))
