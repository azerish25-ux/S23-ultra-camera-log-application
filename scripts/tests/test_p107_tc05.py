"""Tests for TC-P107-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "backlighting",
        "coverage": [0.0, 0.25, 0.5, 1.0],
        "dilated_binary_mask_only": False,
        "halo_px": 1.5,
        "halo_limit_px": 2.0,
    }
    base.update(overrides)
    return base


class TCP10705(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_partial_coverage_inside_the_halo_bound_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("partial_fraction=0.5", result["preservedResults"])

    def test_dilated_binary_mask_is_rejected(self):
        result = evaluate(payload(dilated_binary_mask_only=True, coverage=[0.0, 1.0, 1.0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dilated-binary-person-mask", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_unbounded_halo_is_rejected(self):
        evidence = "p107-smoke"
        result = evaluate(payload(evidenceId=evidence, halo_px=4.0))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("temporal-halo-unbounded", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(coverage=[0.0, 1.4]))
        with self.assertRaises(ValueError):
            evaluate({})
