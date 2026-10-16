"""Tests for TC-P113-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "thermal-advice",
        "manualExposure": True,
        "manualFocus": True,
        "adviceEnabled": True,
        "requestedAngleDegrees": 180,
        "appliedAngleDegrees": 180,
        "fps": 24,
        "clippingWarningsEnabled": True,
        "clippingWarningsDisabledByPreset": False,
        "hiddenSettingChange": False,
        "warningIssued": True,
        "virtualLensApplied": False,
        "virtualLensCompatible": True,
        "sensorConfirmed": False,
        "measurementId": None,
        "syntheticIntegration": False,
    }
    base.update(overrides)
    return base


class TCP11307(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_advice_warns_without_changing_the_manual_shutter(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        self.assertIn("requested-angle-degrees:180", result["preservedResults"])
        focus = evaluate(payload(repeat="focus-warning"))
        self.assertEqual(focus["decision"], "recorded")

    def test_preset_cannot_change_shutter_or_disable_clipping_warnings(self):
        changed = evaluate(payload(appliedAngleDegrees=90))
        self.assert_contract(changed)
        self.assertEqual(changed["decision"], "rejected")
        self.assertIn("preset-changed-shutter", changed["rejectedClaims"])
        self.assertIn("effective-exposure-seconds:1/48", changed["preservedResults"])
        clipped = evaluate(payload(clippingWarningsDisabledByPreset=True))
        self.assertEqual(clipped["decision"], "rejected")
        self.assertIn("preset-disabled-clipping-warnings", clipped["rejectedClaims"])
        hidden = evaluate(payload(hiddenSettingChange=True))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("hidden-camera-setting-change", hidden["rejectedClaims"])
        lens = evaluate(payload(
            repeat="virtual-lens-framing",
            virtualLensApplied=True,
            virtualLensCompatible=False,
        ))
        self.assertEqual(lens["decision"], "rejected")
        self.assertIn("incompatible-virtual-lens-applied", lens["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(requestedAngleDegrees=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(fps=float("nan")))
