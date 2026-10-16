"""Tests for TC-P106-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p106_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p106-evidence",
        "repeat": "Repeat stationary backgrounds with changing foreground occupancy.",
        "source_depths": [0.2, 0.5, 0.8],
        "reported_depths": [0.2, 0.5, 0.8],
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
    }
    base.update(overrides)
    return base


class TCP10603(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P106-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["kept_depths"], [0.2, 0.5, 0.8])
        self.assertEqual(result["preservedResults"][1]["prev_timestamp"], "t0")

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(reported_depths=[0.0, 0.5, 1.0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-minmax-per-frame", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["kept_depths"], [0.2, 0.5, 0.8])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p106-scale"
        result = evaluate(payload(evidenceId=evidence, repeat="foreground occupancy"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(source_depths=[0.2], reported_depths=[0.2]))
        with self.assertRaises(ValueError):
            evaluate(payload(reported_depths=[0.2, 0.5]))
