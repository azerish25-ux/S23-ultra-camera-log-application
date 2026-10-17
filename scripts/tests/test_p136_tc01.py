"""Tests for TC-P136-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc01",
        "repeat": "landscape",
        "report": _GATE.honest_report(),
        "fontScale": 1.6,
        "orientation": "landscape",
        "activeTake": True,
        "advancedOpen": True,
        "recordReachable": True,
        "stopReachable": True,
        "warningsReadable": True,
        "sourceStatusReadable": True,
        "actionsHiddenInScroll": False,
    }
    base.update(overrides)
    return base


class TCP13601(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Landscape and large-text stress")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Open advanced controls with increased font scale in landscape during an active take.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Keep Record or Stop, essential warnings, and selected source status reachable and readable.",
        )
        self.assertEqual(
            _MODULE.CASE["negative"],
            "Critical actions hidden inside scrolling content must fail.",
        )
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat small display settings, orientation changes, and simultaneous audio and storage warnings.",
        )
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "critical-actions-hidden-in-scrolling-content")

    def test_reachable_landscape_controls_are_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("usability acceptance recorded as not run", result["reasons"])
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])
        self.assertTrue(result["preservedResults"][2]["largeTextLandscape"])
        self.assertFalse(result["preservedResults"][2]["measuredOnDevice"])

    def test_actions_hidden_in_scroll_are_rejected(self):
        result = evaluate(payload(actionsHiddenInScroll=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_unreachable_stop_is_rejected(self):
        result = evaluate(payload(stopReachable=False, fontScale=1.0, orientation="portrait"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_screenshot_approval_is_rejected_even_when_controls_fit(self):
        report = _GATE.honest_report(approved=True)
        result = evaluate(payload(report=report))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])
        self.assertIn(_GATE.MUTANT, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc01-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait", orientation="portrait", fontScale=1.0))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][2]["largeTextLandscape"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(fontScale=0))
        with self.assertRaises(ValueError):
            evaluate(payload(orientation="square"))
