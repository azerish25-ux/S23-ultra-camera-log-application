"""Tests for TC-P106-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p106_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p106-evidence",
        "repeat": "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes.",
        "frame_scores": [0.9, 0.95, 0.15, 0.92],
        "catastrophic_threshold": 0.4,
        "report": "separated-catastrophes",
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
    }
    base.update(overrides)
    return base


class TCP10608(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P106-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["severeFrameIndexes"], [2])
        self.assertGreater(record["mean"], 0.7)
        self.assertEqual(record["prev_timestamp"], "t0")
        self.assertEqual(record["curr_timestamp"], "t1")

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(report="mean-only"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mean-hides-severe-boundary-failures", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["severeFrameIndexes"], [2])
        self.assertGreater(result["preservedResults"][1]["mean"], 0.7)

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p106-clip"
        result = evaluate(payload(evidenceId=evidence, repeat="aggressive blur"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frame_scores=[0.9, float("nan"), 0.2]))
        with self.assertRaises(ValueError):
            evaluate(payload(report="best-frame"))
        missing = evaluate(payload(prev_timestamp="", curr_timestamp=None))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn("missing-source-timestamps", missing["rejectedClaims"])
        self.assertIn("p106-evidence", missing["preservedResults"])
