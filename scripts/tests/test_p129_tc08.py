"""Tests for TC-P129-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc08",
        "repeat": "one-handed",
        "event": "thermal",
        "savedVisible": True,
        "nextActionVisible": True,
        "hiddenState": False,
        "mockupSubstitutesForPhysical": False,
        "capture": ["record", "stop"],
        "monitoring": [],
        "processing": [],
        "warnings": ["thermal", "storage"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12908(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Real shooting interruption")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Perform the task on the physical phone with a thermal warning, permission issue, or recovery event.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Let the user understand what was saved and complete the appropriate next action without hidden state.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A desktop mockup cannot substitute for observed physical task completion.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat one-handed operation, outdoor visibility, and finding an interrupted take.",
        )

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("event=thermal", result["preservedResults"])
        self.assertIn("warnings=thermal,storage", result["preservedResults"])
        self.assertIn("host fixture does not substitute for physical S23 task completion", result["reasons"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(mockupSubstitutesForPhysical=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p129-tc08", result["preservedResults"])
        self.assertNotEqual(result["decision"], "qualified")

    def test_hidden_saved_state_and_missing_permission_are_rejected(self):
        result = evaluate(payload(event="permission", warnings=["storage"], savedVisible=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_STATE, result["rejectedClaims"])
        self.assertIn(_MODULE.WARNING_MISSING, result["rejectedClaims"])

    def test_hidden_severe_warning_is_rejected(self):
        result = evaluate(payload(warnings_visible=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("severe-warning-hidden", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(event="desktop"))
