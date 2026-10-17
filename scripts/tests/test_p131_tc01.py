"""Tests for TC-P131-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc01",
        "repeat": "landscape",
        "committed": _GATE.make_control(),
        "proposed": _GATE.held_proposal(),
        "fontScale": 1.6,
        "orientation": "landscape",
        "activeTake": True,
        "recordReachable": True,
        "stopReachable": True,
        "warningsReadable": True,
        "sourceStatusReadable": True,
        "actionsHiddenInScroll": False,
        "sourceStatusText": _GATE.FIXTURE_SOURCE,
    }
    base.update(overrides)
    return base


class TCP13101(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_reachable_landscape_controls_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(result["preservedResults"][1]["draft"], "1.")
        self.assertTrue(result["preservedResults"][1]["record_enabled"])
        self.assertTrue(result["preservedResults"][1]["stop_enabled"])
        self.assertEqual(result["preservedResults"][1]["source_configuration"], _GATE.FIXTURE_SOURCE)
        self.assertEqual(_MODULE.CASE["name"], "Landscape and large-text stress")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "critical-actions-hidden-in-scrolling-content")

    def test_actions_hidden_in_scroll_are_rejected(self):
        result = evaluate(payload(actionsHiddenInScroll=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(result["preservedResults"][1]["source_configuration"], _GATE.FIXTURE_SOURCE)

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc01-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(fontScale=0))
