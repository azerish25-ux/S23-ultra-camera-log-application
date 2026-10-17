"""Tests for TC-P134-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p134_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p134_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p134-tc01",
        "repeat": "landscape",
        "progress": _GATE.fixture_progress(),
        "fontScale": 1.6,
        "orientation": "landscape",
        "activeTake": True,
        "recordReachable": True,
        "stopReachable": True,
        "warningsReadable": True,
        "sourceStatusReadable": True,
        "actionsHiddenInScroll": False,
        "sourceId": "1080p-sdr",
        "sourceStatusText": "1080p-sdr",
    }
    base.update(overrides)
    return base


class TCP13401(unittest.TestCase):
    def assert_contract(self, result, evidence="p134-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P134-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_reachable_landscape_controls_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIsNone(result["preservedResults"][1]["fraction"])
        self.assertFalse(result["preservedResults"][1]["drain_complete"])

    def test_actions_hidden_in_scroll_are_rejected(self):
        result = evaluate(payload(actionsHiddenInScroll=True, repeat="orientation changes"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_source_status_replaced_by_a_look_is_rejected(self):
        result = evaluate(payload(sourceStatusText="IMAX 70mm"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_hundred_percent_during_the_take_is_rejected(self):
        progress = _GATE.fixture_progress(displayed_percent=100, success=True)
        result = evaluate(payload(progress=progress))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.HUNDRED_BEFORE_DRAIN, result["rejectedClaims"])
        self.assertIn(_GATE.PREMATURE_COMPLETE, result["rejectedClaims"])
        self.assertIsNone(result["preservedResults"][1]["fraction"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p134-tc01-repeat"
        result = evaluate(payload(evidenceId=evidence, repeat="audio and storage warnings"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(orientation="sideways"))
        with self.assertRaises(ValueError):
            evaluate(payload(fontScale=0))
