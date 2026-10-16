"""Tests for TC-P118-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def correction(**overrides):
    value = {
        "readoutSecondsPerRow": None,
        "readoutSource": None,
        "cameraVelocityY": 0.0,
        "warpLabel": "none",
        "claimsGlobalShutterRestored": False,
        "rows": [{"rowIndex": 0, "y": 1.0, "velocityY": 0.0, "role": "background"}],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p118-guidance",
        "repeat": "thermal",
        "manualExposure": True,
        "manualFocus": True,
        "adviceEnabled": True,
        "shutterBefore": 180.0,
        "shutterAfter": 180.0,
        "focusBefore": 1.5,
        "focusAfter": 1.5,
        "clippingWarningsBefore": True,
        "clippingWarningsAfter": True,
        "warningIssued": True,
    }
    base.update(correction())
    base.update(overrides)
    return base


class TCP11807(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-guidance"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Guidance overrides user intent")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A cinematic preset that silently disables clipping warnings or changes shutter must fail.",
        )

    def test_warning_without_a_setting_change_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("warning issued without a hidden setting change", result["reasons"])
        kept = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(kept["shutterBefore"], 180.0)
        self.assertEqual(kept["shutterAfter"], 180.0)

    def test_hidden_shutter_focus_and_warning_changes_are_rejected(self):
        result = evaluate(
            payload(
                shutterAfter=90.0,
                focusAfter=3.0,
                clippingWarningsAfter=False,
                repeat="focus-warning",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.WARNING_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.FOCUS_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        kept = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(kept["shutterBefore"], 180.0)
        self.assertEqual(kept["shutterAfter"], 90.0)

    def test_unknown_readout_warp_does_not_shift_rows(self):
        result = evaluate(
            payload(
                **correction(
                    warpLabel="rolling_shutter_correction",
                    rows=[{"rowIndex": 1, "y": 2.0, "velocityY": 6.0, "role": "background"}],
                )
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [2.0])
        self.assertEqual(result["preservedResults"][5], [0.0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(adviceEnabled="yes"))
