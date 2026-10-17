"""Tests for TC-P131-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc08",
        "repeat": "thermal",
        "committed": _GATE.make_control(),
        "proposed": _GATE.held_proposal(),
        "physicalObserved": False,
        "desktopMockupSubstituted": False,
        "savedStateText": "applied 180 source 1080p-sdr",
        "interruption": "thermal",
        "nextAction": "keep the applied shutter and stop or continue",
    }
    base.update(overrides)
    return base


class TCP13108(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_save_is_recorded_without_a_physical_claim(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(result["preservedResults"][1]["source_configuration"], "1080p-sdr")
        self.assertFalse(result["preservedResults"][2]["physicalObserved"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "desktop-mockup-substitutes-for-physical-completion")

    def test_desktop_mockup_cannot_substitute_for_the_phone(self):
        result = evaluate(payload(desktopMockupSubstituted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertIn("p131-tc08", result["preservedResults"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc08-outdoor"
        result = evaluate(payload(evidenceId=evidence, repeat="outdoor", interruption="none"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(interruption="desktop"))
