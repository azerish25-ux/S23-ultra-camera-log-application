"""Tests for TC-P135-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p135_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p135_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p135-tc03",
        "repeat": "shutter",
        "comparison": _GATE.make_comparison(),
        "draftText": "180",
        "draftApplied": False,
        "draftMinimum": 1,
        "draftMaximum": 8000,
    }
    base.update(overrides)
    return base


class TCP13503(unittest.TestCase):
    def assert_contract(self, result, evidence="p135-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unapplied_complete_draft_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["draftKind"], "complete")
        self.assertTrue(result["preservedResults"][2]["draftVisible"])
        self.assertEqual(result["preservedResults"][2]["committedFrame"], 24)
        self.assertTrue(result["preservedResults"][1]["matchedInputs"])

    def test_partial_draft_reaching_the_camera_is_rejected(self):
        result = evaluate(payload(draftText="1/", draftApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["draftKind"], "incomplete")
        self.assertIsNone(result["preservedResults"][2]["draftValue"])

    def test_out_of_range_draft_is_rejected(self):
        result = evaluate(payload(draftText="9000", draftApplied=True, repeat="ISO"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OUT_OF_RANGE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_in_range_apply_keeps_the_comparison(self):
        result = evaluate(payload(draftText="180", draftApplied=True, repeat="focus distance"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][2]["draftVisible"])
        self.assertEqual(result["preservedResults"][1]["left"]["contrast_boost"], 1.0)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(draftMinimum=8, draftMaximum=1))
