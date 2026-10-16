"""Tests for TC-P113-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "reflective",
        "confidence": 0.9,
        "confidenceThreshold": 0.5,
        "synthesized": True,
        "claimedNativeSensorSample": False,
        "provenanceMarksSynthesized": True,
        "crossingObjects": True,
        "interpolationApplied": True,
        "disocclusionBounded": True,
        "shutterAngleDegrees": 180,
        "fps": 24,
        "sensorConfirmed": False,
        "measurementId": None,
        "syntheticIntegration": False,
    }
    base.update(overrides)
    return base


class TCP11304(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_bounded_synthesis_is_recorded_and_marked(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("provenance:synthesized", result["preservedResults"])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])

    def test_native_claim_and_unbounded_occlusion_are_rejected(self):
        native = evaluate(payload(claimedNativeSensorSample=True))
        self.assert_contract(native)
        self.assertEqual(native["decision"], "rejected")
        self.assertIn("interpolated-frame-called-native", native["rejectedClaims"])
        unmarked = evaluate(payload(provenanceMarksSynthesized=False))
        self.assertEqual(unmarked["decision"], "rejected")
        self.assertIn("synthesized-frame-unmarked", unmarked["rejectedClaims"])
        unbounded = evaluate(payload(disocclusionBounded=False))
        self.assertEqual(unbounded["decision"], "rejected")
        self.assertIn("occlusion-unbounded", unbounded["rejectedClaims"])

    def test_low_confidence_falls_back_instead_of_interpolating(self):
        fallback = evaluate(payload(
            repeat="thin-fast",
            confidence=0.2,
            interpolationApplied=False,
        ))
        self.assertEqual(fallback["decision"], "recorded")
        self.assertIn("fell back under confidence policy", " ".join(fallback["reasons"]))
        forced = evaluate(payload(
            repeat="repetitive-pattern",
            confidence=0.2,
            interpolationApplied=True,
        ))
        self.assertEqual(forced["decision"], "rejected")
        self.assertIn("unbounded-interpolation", forced["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(confidence=float("nan")))
        with self.assertRaises(ValueError):
            evaluate(payload(fps=-2))
