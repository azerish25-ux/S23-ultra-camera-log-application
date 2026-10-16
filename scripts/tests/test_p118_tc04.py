"""Tests for TC-P118-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc04.py",
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
        "evidenceId": "p118-occlusion",
        "repeat": "reflective",
        "confidence": 0.9,
        "confidenceFloor": 0.5,
        "occlusionPresent": False,
        "artifactScore": 0.1,
        "artifactBound": 0.4,
        "fallbackApplied": False,
        "samples": [{"time": 0.5, "origin": "estimated"}],
    }
    base.update(correction())
    base.update(overrides)
    return base


class TCP11804(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-occlusion"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Interpolation occlusion artifact")
        self.assertEqual(_MODULE.NEGATIVE, "Calling interpolated frames native sensor samples must fail.")

    def test_bounded_estimated_sample_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn(["estimated"], result["preservedResults"])

    def test_captured_label_is_rejected(self):
        result = evaluate(payload(samples=[{"time": 0.5, "origin": "captured"}]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn(["captured"], result["preservedResults"])

    def test_low_confidence_without_fallback_is_rejected(self):
        result = evaluate(
            payload(
                confidence=0.2,
                occlusionPresent=True,
                artifactScore=0.9,
                fallbackApplied=False,
                repeat="thin-fast",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOW_CONFIDENCE, result["rejectedClaims"])
        self.assertIn(_MODULE.UNBOUNDED, result["rejectedClaims"])

    def test_fallback_can_be_recorded(self):
        result = evaluate(payload(confidence=0.1, fallbackApplied=True, repeat="repetitive"))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("fallback retains origin=estimated", result["reasons"])

    def test_unknown_readout_warp_does_not_shift_rows(self):
        result = evaluate(
            payload(
                **correction(
                    warpLabel="rolling_shutter_correction",
                    rows=[{"rowIndex": 2, "y": 6.0, "velocityY": 3.0, "role": "foreground"}],
                )
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"][4], [6.0])
        self.assertEqual(result["preservedResults"][5], [0.0])
        self.assertIn("correction_applied false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(samples=[]))
