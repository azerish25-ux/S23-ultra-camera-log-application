"""Tests for TC-P106-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p106_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _point(x, y, depth, dx, dy):
    return {"x": x, "y": y, "depth": depth, "dx": dx, "dy": dy, "rdx": -dx, "rdy": -dy}


def payload(**overrides):
    base = {
        "evidenceId": "p106-evidence",
        "repeat": "Repeat translation, rotation, scale change, and camera motion.",
        "frame_width": 8,
        "frame_height": 8,
        "motion_px": 3,
        "points": [_point(2, 2, 0.4, 3, 0)],
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
    }
    base.update(overrides)
    return base


class TCP10601(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P106-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        sample = result["preservedResults"][1]["samples"][0]
        self.assertEqual((sample["x"], sample["y"], sample["depth"], sample["status"]), (5, 2, 0.4, "measured"))
        self.assertEqual(result["preservedResults"][1]["prev_timestamp"], "t0")
        self.assertEqual(result["preservedResults"][1]["curr_timestamp"], "t1")

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(points=[_point(2, 2, 0.4, 0, 0)]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stationary-pixel-average-depth-trails", result["rejectedClaims"])
        sample = result["preservedResults"][1]["samples"][0]
        self.assertEqual(sample["x"], 2)
        self.assertEqual(sample["y"], 2)

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p106-with"
        result = evaluate(payload(evidenceId=evidence, repeat="with rotation"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(prev_timestamp=" t0"))
        with self.assertRaises(ValueError):
            evaluate(payload(motion_px=True))
