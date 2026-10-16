"""Tests for TC-P119-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p119_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p119_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _guidance(**overrides):
    statement = {
        "text": "clipping stays visible while exposure stays manual",
        "limitId": "mode-24",
        "recommendsFps": None,
        "recommendsShutter": None,
        "observedMotionPx": 1.0,
        "claimsStableMotion": True,
        "promises": [],
    }
    statement.update(overrides)
    return [statement]


def payload(**overrides):
    base = {
        "evidenceId": "p119-guidance",
        "adviceEnabled": True,
        "manualExposure": True,
        "manualFocus": True,
        "shutterChanged": False,
        "clippingWarningsDisabled": False,
        "hiddenChange": False,
        "repeat": "focus-warning",
        "selectedLimitId": "mode-24",
        "measuredLimits": [
            {
                "id": "mode-24",
                "fps": 24.0,
                "shutter_angle": 180.0,
                "max_stable_motion_px": 8.0,
                "mode_available": True,
            }
        ],
        "guidance": _guidance(),
    }
    base.update(overrides)
    return base


class TCP11907(unittest.TestCase):
    def assert_contract(self, result, evidence="p119-guidance"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P119-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Guidance overrides user intent")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A cinematic preset that silently disables clipping warnings or changes shutter must fail.",
        )
        self.assertIn("virtual-lens framing", _MODULE.REPEAT)

    def test_suggestion_only_advice_is_recorded(self):
        result = evaluate(payload(repeat="thermal-advice"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][1]["shutterChanged"])

    def test_silent_shutter_change_is_rejected(self):
        result = evaluate(payload(shutterChanged=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-shutter-change", result["rejectedClaims"])
        self.assertIn("guidance-overrides-manual-intent", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["shutterChanged"])

    def test_disabled_clipping_warnings_are_rejected(self):
        result = evaluate(payload(clippingWarningsDisabled=True, repeat="incompatible-virtual-lens"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-clipping-warning-disable", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_ungrounded_advice_is_rejected_without_changing_shutter(self):
        result = evaluate(payload(guidance=_guidance(limitId=None, text="open the iris one stop")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("ungrounded-guidance", result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["shutterChanged"])
        self.assertFalse(result["preservedResults"][1]["clippingWarningsDisabled"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(hiddenChange=1))
