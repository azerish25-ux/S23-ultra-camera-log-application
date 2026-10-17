"""Tests for TC-P132-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc03",
        "repeat": "shutter",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "draftText": "0.",
        "draftApplied": False,
        "draftMinimum": 0,
        "draftMaximum": 1,
    }
    base.update(overrides)
    return base


def clipping_count(result):
    scopes = result["preservedResults"][1]["scopes"]
    return next(item["clippingCount"] for item in scopes if item["id"] == "preview-clipping")


class TCP13203(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unapplied_incomplete_draft_keeps_the_declared_count(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(clipping_count(result), 3)
        self.assertEqual(result["preservedResults"][2]["declaredThreshold"], 0.95)
        self.assertEqual(result["preservedResults"][2]["draftKind"], "incomplete")
        self.assertFalse(result["preservedResults"][2]["draftApplied"])

    def test_applied_partial_draft_is_rejected_and_count_remains(self):
        result = evaluate(payload(draftApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(clipping_count(result), 3)

    def test_applied_out_of_range_draft_is_rejected(self):
        result = evaluate(payload(draftText="2", draftApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OUT_OF_RANGE, result["rejectedClaims"])
        self.assertEqual(clipping_count(result), 3)

    def test_applied_in_range_draft_does_not_replace_the_threshold(self):
        result = evaluate(payload(draftText="0.5", draftApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(clipping_count(result), 3)
        self.assertEqual(result["preservedResults"][2]["declaredThreshold"], 0.95)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(draftMinimum=2, draftMaximum=1))
