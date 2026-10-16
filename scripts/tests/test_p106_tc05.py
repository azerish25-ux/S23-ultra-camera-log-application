"""Tests for TC-P106-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p106_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p106-evidence",
        "repeat": "Repeat backlighting, crossing subjects, and different foreground-background contrast.",
        "frame_width": 8,
        "frame_height": 8,
        "points": [
            {"x": 2, "y": 2, "depth": 0.3, "dx": 1, "dy": 0, "rdx": -1, "rdy": 0, "coverage": 0.4},
            {"x": 4, "y": 2, "depth": 0.9, "dx": 1, "dy": 0, "rdx": -1, "rdy": 1.5, "coverage": 1},
        ],
        "fill_unknowns_as_measured": False,
        "dilated_binary_mask_only": False,
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
    }
    base.update(overrides)
    return base


class TCP10605(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P106-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        samples = result["preservedResults"][1]["samples"]
        self.assertEqual(samples[0]["status"], "partial")
        self.assertEqual(samples[0]["depth"], 0.3)
        self.assertEqual(samples[1]["status"], "unknown")
        self.assertIsNone(samples[1]["depth"])
        self.assertEqual(samples[1]["cause"], "forward-backward-inconsistent")

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(dilated_binary_mask_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dilated-binary-person-mask-not-boundary-quality", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["samples"][0]["status"], "partial")

    def test_neighbour_fill_of_unknowns_is_rejected(self):
        result = evaluate(payload(fill_unknowns_as_measured=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unknowns-filled-from-neighbours-called-measured", result["rejectedClaims"])
        self.assertIsNone(result["preservedResults"][1]["samples"][1]["depth"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p106-hair-edge"
        result = evaluate(payload(evidenceId=evidence, repeat="backlighting"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(points=[{
                "x": 2, "y": 2, "depth": 0.3, "dx": 1, "dy": 0, "coverage": 1.2,
            }]))
