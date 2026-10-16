"""Tests for TC-P112-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frames(aligned=True):
    rows = []
    for index in range(4):
        object_x = float(index)
        rows.append({
            "object_x": object_x,
            "history_x": object_x if aligned else 0.0,
            "depth": 1.5 + (0.1 * index),
        })
    return rows


def payload(**overrides):
    base = {
        "evidenceId": "p112-tc01",
        "repeat": "translation",
        "frames": frames(True),
    }
    base.update(overrides)
    return base


class TCP11201(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_warped_history_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_stationary_pixel_average_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(frames=frames(False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stationary-pixel-average-depth-trail", result["rejectedClaims"])
        self.assertTrue(any("depth=" in item for item in result["preservedResults"]))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p112-tc01-rotation"
        result = evaluate(payload(evidenceId=evidence, repeat="rotation"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[{"object_x": 0.0, "history_x": 0.0, "depth": 1.0}]))
