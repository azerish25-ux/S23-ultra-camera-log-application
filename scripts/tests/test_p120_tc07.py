"""Tests for TC-P120-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def honest_report(**overrides):
    value = {
        "shutter_angle": 180.0,
        "fps": 24.0,
        "exposure_seconds": (180.0 / 360.0) / 24.0,
        "interpolation_fraction": 0.0,
        "estimated_disclosed": False,
        "stabilization_crop_fraction": 0.0,
        "rolling_shutter_readout": "unknown",
        "correction_applied": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p120-evidence",
        "repeat": "Repeat",
        "combinationPassed": True,
        "report": honest_report(),
        "manualExposure": True,
        "manualFocus": True,
        "adviceEnabled": True,
        "shutterBefore": 180.0,
        "shutterAfter": 180.0,
        "focusBefore": 2.0,
        "focusAfter": 2.0,
        "clippingWarningsBefore": True,
        "clippingWarningsAfter": True,
        "warningIssued": True,
    }
    base.update(overrides)
    return base


class TCP12007(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_warning_without_a_hidden_change_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("warning issued" in item for item in result["reasons"]))

    def test_hidden_shutter_change_is_rejected(self):
        result = evaluate(payload(
            shutterAfter=90.0,
            report=honest_report(shutter_angle=90.0, exposure_seconds=(90.0 / 360.0) / 24.0),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_disabled_clipping_warnings_are_rejected(self):
        result = evaluate(payload(clippingWarningsAfter=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WARNING_TOKEN, result["rejectedClaims"])

    def test_hidden_focus_change_is_rejected(self):
        result = evaluate(payload(focusAfter=4.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOCUS_TOKEN, result["rejectedClaims"])

    def test_report_shutter_that_disagrees_with_manual_is_rejected(self):
        result = evaluate(payload(report=honest_report(
            shutter_angle=90.0,
            exposure_seconds=(90.0 / 360.0) / 24.0,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="thermal advice"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
