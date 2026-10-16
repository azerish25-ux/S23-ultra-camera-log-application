"""Tests for TC-P106-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p106_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p106-evidence",
        "repeat": "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem.",
        "foreground_depth": 0.3,
        "background_depth": 0.9,
        "foreground_coverage": 1.0,
        "model": "layered-coverage",
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
    }
    base.update(overrides)
    return base


class TCP10607(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P106-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        layers = result["preservedResults"][1]["layers"]
        self.assertEqual(layers["energy"], 1.0)
        self.assertEqual(layers["background_status"], "unknown")
        self.assertEqual(result["preservedResults"][1]["prev_timestamp"], "t0")
        self.assertTrue(any("approximation" in reason for reason in result["reasons"]))

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(model="uniform-background-blur"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("uniform-background-blur-without-foreground-coverage", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p106-bokeh"
        result = evaluate(payload(evidenceId=evidence, repeat="estimated-depth", foreground_coverage=0.5))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["layers"]["background_status"], "partial")
        self.assertEqual(result["preservedResults"][1]["layers"]["background_weight"], 0.5)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(foreground_depth=1.2, background_depth=0.4))
        with self.assertRaises(ValueError):
            evaluate(payload(foreground_coverage=1.4))
