"""Tests for TC-P129-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc07",
        "repeat": "source-versus-result",
        "leftTime": 1.0,
        "rightTime": 1.0,
        "leftScale": 1.0,
        "rightScale": 1.0,
        "leftTransform": "display-sdr",
        "rightTransform": "display-sdr",
        "leftEnhanced": False,
        "rightEnhanced": False,
        "mismatchDisclosed": False,
        "preferencePresented": True,
        "capture": ["record", "stop"],
        "monitoring": [],
        "processing": [],
        "warnings": ["storage"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12907(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Unfair comparison view")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Compare outputs at different times, scales, or display transforms without making those differences visible.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Align comparable content or clearly disclose the mismatch before presenting a preference judgment.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Automatically enhancing one side of a comparison must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat source-versus-result, recipe revisions, and different output aspect ratios.",
        )

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("aligned=true", result["preservedResults"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(rightEnhanced=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p129-tc07", result["preservedResults"])

    def test_undisclosed_mismatch_is_rejected(self):
        result = evaluate(payload(rightTime=2.0, rightScale=1.5, rightTransform="hlg"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDISCLOSED, result["rejectedClaims"])

    def test_disclosed_mismatch_is_recorded(self):
        result = evaluate(payload(
            evidenceId="p129-tc07-disclosed",
            rightScale=1.5,
            mismatchDisclosed=True,
        ))
        self.assert_contract(result, "p129-tc07-disclosed")
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("aligned=false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(leftScale=0))
