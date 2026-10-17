"""Tests for TC-P135-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p135_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p135_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p135-tc08",
        "repeat": "one-handed operation",
        "comparison": _GATE.make_comparison(),
        "physicalObserved": False,
        "desktopMockupSubstituted": False,
        "savedComparisonDisclosed": True,
        "interruption": "thermal",
        "nextAction": "review the saved comparison and resume when the warning clears",
    }
    base.update(overrides)
    return base


class TCP13508(unittest.TestCase):
    def assert_contract(self, result, evidence="p135-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_interruption_is_recorded_without_a_physical_claim(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][2]["physicalObserved"])
        self.assertTrue(result["preservedResults"][2]["savedComparisonDisclosed"])
        self.assertEqual(result["preservedResults"][2]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)
        self.assertTrue(result["preservedResults"][1]["matchedInputs"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "desktop-mockup-substitutes-for-physical-completion")

    def test_desktop_mockup_is_rejected(self):
        result = evaluate(payload(desktopMockupSubstituted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_claimed_physical_observation_is_rejected(self):
        result = evaluate(payload(physicalObserved=True, interruption="permission", repeat="outdoor visibility"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNOBSERVED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_hidden_save_is_rejected(self):
        result = evaluate(payload(savedComparisonDisclosed=False, interruption="recovery"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_SAVE, result["rejectedClaims"])

    def test_contrast_boost_still_rejects_during_an_interruption(self):
        comparison = _GATE.replace_side(_GATE.make_comparison(), "right", contrast_boost=2)
        result = evaluate(payload(comparison=comparison, repeat="finding an interrupted take"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.CONTRAST_NOT_UNITY, result["rejectedClaims"])
        self.assertIn(_GATE.FIXTURE_SOURCE_SHA256, result["preservedResults"][1]["left"]["source_sha256"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(interruption="battery"))
