"""Tests for TC-P133-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SAVED = "1080p SDR saved"


def saved_controls():
    return _GATE.replace_control(_GATE.fixture_controls(), "source-status", state_description=SAVED)


def payload(**overrides):
    base = {
        "evidenceId": "p133-tc08",
        "repeat": "one-handed operation",
        "controls": saved_controls(),
        "focusOrder": _GATE.fixture_focus_order(),
        "physicalObserved": False,
        "desktopMockupSubstituted": False,
        "savedStateDisclosed": True,
        "savedStateText": SAVED,
        "interruption": "thermal",
        "nextAction": "keep the retained 1080p SDR source and retry the take",
    }
    base.update(overrides)
    return base


class TCP13308(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_save_is_recorded_without_a_physical_claim(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][2]["physicalObserved"])
        self.assertTrue(result["preservedResults"][2]["savedStateAnnounced"])
        self.assertEqual(result["preservedResults"][2]["interruption"], "thermal")
        self.assertIn("record", result["preservedResults"][1]["focusOrder"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "desktop-mockup-substitutes-for-physical-completion")

    def test_desktop_mockup_cannot_substitute_for_the_phone(self):
        result = evaluate(payload(desktopMockupSubstituted=True, repeat="outdoor visibility"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p133-tc08", result["preservedResults"])

    def test_claimed_physical_observation_is_rejected(self):
        result = evaluate(payload(physicalObserved=True, interruption="permission"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNOBSERVED, result["rejectedClaims"])

    def test_hidden_save_is_rejected(self):
        result = evaluate(
            payload(savedStateDisclosed=False, savedStateText="nothing retained", repeat="finding an interrupted take")
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_SAVE, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][2]["savedStateAnnounced"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(interruption="rain"))
        with self.assertRaises(ValueError):
            evaluate(payload(physicalObserved="yes"))
