"""Tests for TC-P109-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")

FRAMES = [
    {"background": [0.4, 0.4], "foreground": [0.1]},
    {"background": [0.4, 0.4], "foreground": [0.9]},
]


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "stationary background",
        "mode": "shared",
        "frames": FRAMES,
    }
    base.update(overrides)
    return base


class TCP10903(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-03")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_shared_scale_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("shared-scale normalized-background 0.375000,0.375000", result["reasons"])

    def test_negative_per_frame_minmax_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(mode="per-frame-minmax"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-minmax-normalization", result["rejectedClaims"])
        self.assertIn("normalized-background 1.000000,0.000000", " ".join(result["reasons"]))

    def test_mutant_per_frame_minmax_is_rejected(self):
        result = evaluate(payload(mode="per-frame-minmax", repeat="changing occupancy"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-minmax-normalization", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p109-reset"
        result = evaluate(payload(evidenceId=evidence, repeat="reset", mode="reset"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
