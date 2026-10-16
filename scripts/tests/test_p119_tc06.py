"""Tests for TC-P119-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p119_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p119_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _guidance(**overrides):
    statement = {
        "text": "restrict the correction to the measured camera motion",
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
        "evidenceId": "p119-rolling",
        "independentForeground": True,
        "correction": "restricted",
        "advertisedUniversal": False,
        "readoutKnown": True,
        "repeat": "moving-subject",
        "selectedLimitId": "mode-24",
        "measuredLimits": [
            {
                "id": "mode-24",
                "fps": 24.0,
                "shutter_angle": 172.8,
                "max_stable_motion_px": 8.0,
                "mode_available": True,
            }
        ],
        "guidance": _guidance(),
    }
    base.update(overrides)
    return base


class TCP11906(unittest.TestCase):
    def assert_contract(self, result, evidence="p119-rolling"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P119-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Rolling-shutter model violation")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "One global shear must not be advertised as universal rolling-shutter removal.",
        )
        self.assertIn("unknown readout timing", _MODULE.REPEAT)

    def test_restricted_correction_is_recorded(self):
        result = evaluate(payload(repeat="pan"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("correction:restricted", result["preservedResults"])

    def test_global_shear_on_foreground_is_rejected(self):
        result = evaluate(payload(correction="global-shear", repeat="vibration"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unjustified-global-warp", result["rejectedClaims"])
        self.assertIn("correction:global-shear", result["preservedResults"])

    def test_universal_advertisement_and_unknown_readout_are_rejected(self):
        advertised = evaluate(payload(advertisedUniversal=True))
        self.assertEqual(advertised["decision"], "rejected")
        self.assertIn("global-shear-as-universal-rolling-shutter-removal", advertised["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, advertised["reasons"])
        unknown = evaluate(
            payload(
                independentForeground=False,
                correction="global-shear",
                readoutKnown=False,
                repeat="unknown-readout",
            )
        )
        self.assertEqual(unknown["decision"], "rejected")
        self.assertIn("unknown-readout-global-warp", unknown["rejectedClaims"])
        clean = evaluate(
            payload(
                evidenceId="p119-global-ok",
                independentForeground=False,
                correction="global-shear",
                readoutKnown=True,
                repeat="pan",
            )
        )
        self.assert_contract(clean, "p119-global-ok")
        self.assertEqual(clean["decision"], "recorded")

    def test_honest_180_limit_is_recorded_with_a_restricted_correction(self):
        result = evaluate(
            payload(
                evidenceId="p119-honest-roll",
                guidance=_guidance(text="this mode cannot do 180 degrees at this fps"),
            )
        )
        self.assert_contract(result, "p119-honest-roll")
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("honest-180:" in item for item in result["reasons"]))
        self.assertIn("correction:restricted", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(correction="magic"))
