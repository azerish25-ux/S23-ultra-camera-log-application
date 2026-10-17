"""Tests for TC-P133-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p133-tc01",
        "repeat": "landscape",
        "controls": _GATE.fixture_controls(),
        "focusOrder": _GATE.fixture_focus_order(),
        "fontScale": 1.6,
        "orientation": "landscape",
        "activeTake": True,
        "actionsHiddenInScroll": False,
        "baselineFocusOrder": _GATE.fixture_focus_order(),
    }
    base.update(overrides)
    return base


class TCP13301(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_large_text_landscape_keeps_record_stop_and_warnings(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["minimumTargetSize"], 48)
        self.assertTrue(result["preservedResults"][1]["focusIncludesRecord"])
        self.assertTrue(result["preservedResults"][1]["focusIncludesStop"])
        self.assertTrue(result["preservedResults"][2]["criticalReachable"])
        self.assertTrue(result["preservedResults"][2]["focusPreserved"])
        self.assertEqual(_MODULE.CASE["name"], "Landscape and large-text stress")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "critical-actions-hidden-in-scrolling-content")

    def test_actions_hidden_in_scroll_are_rejected(self):
        result = evaluate(payload(actionsHiddenInScroll=True, repeat="small display"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("record", result["preservedResults"][1]["focusOrder"])
        self.assertIn("stop", result["preservedResults"][1]["focusOrder"])

    def test_focus_order_drift_across_orientation_is_rejected(self):
        drifted = list(reversed(_GATE.fixture_focus_order()))
        result = evaluate(payload(focusOrder=drifted, orientation="portrait", repeat="orientation"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOCUS_DRIFT, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["focusOrder"], drifted)

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p133-tc01-portrait"
        result = evaluate(
            payload(evidenceId=evidence, repeat="portrait", orientation="portrait", fontScale=1.0)
        )
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(fontScale=0))
        with self.assertRaises(ValueError):
            evaluate(payload(orientation="square"))
