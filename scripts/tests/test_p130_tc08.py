"""Tests for TC-P130-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p130_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p130_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p130-tc08",
        "repeat": "one-handed operation",
        "committed": _GATE.make_selection(),
        "proposed": _GATE.imax_proposal(),
        "physicalObserved": False,
        "desktopMockupSubstituted": False,
        "savedSourceDisclosed": True,
        "interruption": "thermal",
        "nextAction": "keep the retained 1080p SDR source and retry the take",
    }
    base.update(overrides)
    return base


class TCP13008(unittest.TestCase):
    def assert_contract(self, result, evidence="p130-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P130-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_save_is_recorded_without_a_physical_claim(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["source_retained"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(result["preservedResults"][2]["interruption"], "thermal")
        self.assertFalse(result["preservedResults"][2]["physicalObserved"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "desktop-mockup-substitutes-for-physical-completion")

    def test_desktop_mockup_cannot_substitute_for_the_phone(self):
        result = evaluate(payload(desktopMockupSubstituted=True, repeat="outdoor visibility"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"][1]["source_id"], _GATE.FIXTURE_SOURCE_ID)

    def test_claimed_physical_observation_is_rejected(self):
        result = evaluate(payload(physicalObserved=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNOBSERVED, result["rejectedClaims"])

    def test_hidden_save_is_rejected_and_source_bytes_remain_in_evidence(self):
        result = evaluate(payload(savedSourceDisclosed=False, repeat="finding an interrupted take"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_SAVE, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)

    def test_deleted_source_bytes_are_rejected_on_a_cleared_look(self):
        proposed = _GATE.make_selection(look_id=None, look_params=None, source_retained=False)
        result = evaluate(payload(proposed=proposed, interruption="recovery"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.SOURCE_NOT_RETAINED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["source_transfer"], "bt709")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(interruption="rain"))
        with self.assertRaises(ValueError):
            evaluate(payload(nextAction=" "))
