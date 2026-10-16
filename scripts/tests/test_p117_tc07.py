"""Tests for TC-P117-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def geometry(**overrides):
    value = _MODULE._CORE.recorded_geometry()
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p117-guidance",
        "repeat": "thermal-advice",
        "manualExposure": True,
        "manualFocus": True,
        "shutterBefore": 180.0,
        "shutterAfter": 180.0,
        "focusBefore": 1.5,
        "focusAfter": 1.5,
        "clippingWarningsBefore": True,
        "clippingWarningsAfter": True,
        "warningIssued": True,
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11707(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-guidance"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Guidance overrides user intent")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A cinematic preset that silently disables clipping warnings or changes shutter must fail.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat thermal advice, focus warnings, and incompatible virtual-lens framing.",
        )

    def test_warning_without_a_setting_change_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("shutter=180->180", result["preservedResults"])
        self.assertIn("focus=1.5->1.5", result["preservedResults"])

    def test_hidden_shutter_change_is_rejected(self):
        result = evaluate(payload(shutterAfter=90.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("shutter=180->90", result["preservedResults"])

    def test_disabled_clipping_warnings_are_rejected(self):
        result = evaluate(payload(clippingWarningsAfter=False, repeat="focus-warnings"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WARNING_TOKEN, result["rejectedClaims"])

    def test_hidden_focus_change_is_rejected(self):
        result = evaluate(payload(focusAfter=3.0, repeat="focus-warnings"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOCUS_TOKEN, result["rejectedClaims"])

    def test_virtual_lens_aspect_without_a_recorded_crop_is_rejected(self):
        geo = geometry(cropRecorded=False)
        result = evaluate(payload(geometry=geo, repeat="incompatible-virtual-lens-framing"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-aspect-changing-crop", result["rejectedClaims"])
        self.assertIn("shutter=180->180", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
