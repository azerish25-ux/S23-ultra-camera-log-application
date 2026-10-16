"""Tests for TC-P106-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p106_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p106-evidence",
        "repeat": "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking.",
        "frame_width": 8,
        "frame_height": 8,
        "subjects": [
            {"id": "user", "x": 1, "y": 1, "depth": 0.6, "dx": 3, "dy": 0, "selected": True},
            {"id": "other", "x": 4, "y": 1, "depth": 0.2, "dx": -3, "dy": 0, "selected": False},
        ],
        "selection_policy": "documented-identity",
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
    }
    base.update(overrides)
    return base


class TCP10606(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P106-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["focusId"], "user")
        user = next(sample for sample in record["samples"] if sample["id"] == "user")
        other = next(sample for sample in record["samples"] if sample["id"] == "other")
        self.assertEqual((user["x"], user["depth"]), (4, 0.6))
        self.assertEqual((other["x"], other["depth"]), (1, 0.2))
        self.assertLess(other["depth"], user["depth"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(selection_policy="nearest-face"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("nearest-face-independently-each-frame", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["focusId"], "user")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p106-cross"
        result = evaluate(payload(evidenceId=evidence, repeat="re-entry"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(selection_policy="nearest-depth"))
        with self.assertRaises(ValueError):
            evaluate(payload(subjects=[
                {"id": "user", "x": 1, "y": 1, "depth": 0.6, "dx": 1, "dy": 0, "selected": True},
            ]))
