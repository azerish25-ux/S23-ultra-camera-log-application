"""Tests for TC-P106-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p106_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p106-evidence",
        "repeat": "Repeat thin objects, hands, hair, and large foreground occluders.",
        "frame_width": 6,
        "frame_height": 4,
        "points": [{"x": 2, "y": 1, "depth": 0.25, "dx": 2, "dy": 0, "rdx": -2, "rdy": 0}],
        "revealed_pixels": [{"x": 2, "y": 1}],
        "filled_depth": None,
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
    }
    base.update(overrides)
    return base


class TCP10602(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P106-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["samples"][0]["x"], 4)
        self.assertEqual(record["samples"][0]["depth"], 0.25)
        self.assertEqual(record["revealed"][0]["status"], "unknown")
        self.assertIsNone(record["revealed"][0]["depth"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(filled_depth=0.25))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filled-newly-visible-with-old-depth", result["rejectedClaims"])
        self.assertIsNone(result["preservedResults"][1]["revealed"][0]["depth"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p106-hair"
        result = evaluate(payload(evidenceId=evidence, repeat="hair"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(revealed_pixels=[{"x": -1, "y": 1}]))
        with self.assertRaises(ValueError):
            evaluate(payload(filled_depth=float("nan")))
