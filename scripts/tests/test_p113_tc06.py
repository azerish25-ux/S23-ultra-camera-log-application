"""Tests for TC-P113-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "pans",
        "independentForegroundMotion": False,
        "globalShearApplied": False,
        "advertisedAsUniversalRemoval": False,
        "readoutTimingKnown": True,
        "correctionRestricted": True,
        "shutterAngleDegrees": 180,
        "fps": 24,
        "sensorConfirmed": False,
        "measurementId": None,
        "syntheticIntegration": False,
    }
    base.update(overrides)
    return base


class TCP11306(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_restricted_pan_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        moving = evaluate(payload(
            repeat="moving-subjects",
            independentForegroundMotion=True,
            globalShearApplied=False,
            correctionRestricted=True,
        ))
        self.assertEqual(moving["decision"], "recorded")

    def test_universal_shear_and_unknown_readout_are_rejected(self):
        universal = evaluate(payload(advertisedAsUniversalRemoval=True, globalShearApplied=True))
        self.assert_contract(universal)
        self.assertEqual(universal["decision"], "rejected")
        self.assertIn("global-shear-as-universal-rolling-shutter-removal", universal["rejectedClaims"])
        warp = evaluate(payload(
            repeat="moving-subjects",
            independentForegroundMotion=True,
            globalShearApplied=True,
            correctionRestricted=False,
        ))
        self.assertEqual(warp["decision"], "rejected")
        self.assertIn("unjustified-global-warp", warp["rejectedClaims"])
        unknown = evaluate(payload(
            repeat="unknown-readout",
            readoutTimingKnown=False,
            globalShearApplied=True,
            correctionRestricted=False,
        ))
        self.assertEqual(unknown["decision"], "rejected")
        self.assertIn("unknown-readout-global-shear", unknown["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(fps=0))
        with self.assertRaises(ValueError):
            evaluate(payload(shutterAngleDegrees=float("inf")))
