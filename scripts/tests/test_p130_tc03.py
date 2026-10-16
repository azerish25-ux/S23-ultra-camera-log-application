"""Tests for TC-P130-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p130_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p130_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p130-tc03",
        "repeat": "shutter",
        "committed": _GATE.make_selection(),
        "proposed": _GATE.imax_proposal(),
        "draftText": "180.",
        "draftApplied": False,
        "draftMinimum": 1,
        "draftMaximum": 360,
    }
    base.update(overrides)
    return base


class TCP13003(unittest.TestCase):
    def assert_contract(self, result, evidence="p130-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P130-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_interrupted_partial_draft_stays_unapplied(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["draftKind"], "incomplete")
        self.assertFalse(result["preservedResults"][2]["draftApplied"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "partial-draft-reached-camera")

    def test_partial_draft_reaching_the_camera_is_rejected(self):
        result = evaluate(payload(draftApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["source_transfer"], "bt709")

    def test_out_of_range_applied_draft_is_rejected(self):
        result = evaluate(payload(draftText="400", draftApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OUT_OF_RANGE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_in_range_applied_draft_keeps_the_source(self):
        result = evaluate(payload(draftText="172.8", draftApplied=True, repeat="ISO"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["draftValue"], 172.8)
        self.assertEqual(result["preservedResults"][1]["changedSourceFields"], [])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(draftMinimum=10, draftMaximum=1))
