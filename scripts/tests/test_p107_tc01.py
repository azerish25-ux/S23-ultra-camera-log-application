"""Tests for TC-P107-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "translation",
        "dx": 4.0,
        "dy": 0.0,
        "history_warped": True,
        "stationary_pixel_average": False,
    }
    base.update(overrides)
    return base


class TCP10701(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_warped_history_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("motion_px=4", result["preservedResults"])

    def test_stationary_pixel_average_is_rejected(self):
        result = evaluate(payload(stationary_pixel_average=True, history_warped=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stationary-pixel-average", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_unwarped_motion_is_rejected(self):
        result = evaluate(payload(history_warped=False, dx=3.0, dy=4.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unaligned-history", result["rejectedClaims"])
        self.assertIn("motion_px=5", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p107-rotation"
        result = evaluate(payload(evidenceId=evidence, repeat="rotation", dx=0.0, dy=0.0, history_warped=False))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
