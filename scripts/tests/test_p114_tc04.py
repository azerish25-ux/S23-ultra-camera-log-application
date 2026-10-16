"""Tests for TC-P114-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "reflective objects",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [{"origin": "captured", "weight": 1.0, "synthesized": False, "confidence": 1.0}],
        "confidence_floor": 0.5,
        "fell_back": False,
    }
    base.update(overrides)
    return base


class TCP11404(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_captured_frame_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_interpolated_frame_called_native_is_rejected(self):
        result = evaluate(payload(
            frames=[{"origin": "captured", "weight": 1.0, "synthesized": True, "confidence": 0.9}],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("interpolated-frames-called-native-sensor-samples", result["rejectedClaims"])

    def test_low_confidence_falls_back_only_when_marked_estimated(self):
        recorded = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0, "synthesized": True, "confidence": 0.2}],
            contains_estimated=True,
            disclosed=True,
            fell_back=True,
            repeat="thin fast structures",
        ))
        self.assertEqual(recorded["decision"], "recorded")
        rejected = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0, "synthesized": True, "confidence": 0.2}],
            contains_estimated=True,
            disclosed=True,
            fell_back=False,
        ))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("low-confidence-without-fallback", rejected["rejectedClaims"])

    def test_hidden_estimate_and_scope_failures_are_rejected(self):
        hidden = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0, "synthesized": True, "confidence": 1.0}],
            contains_estimated=True,
            disclosed=False,
        ))
        self.assertIn("hidden-hallucination", hidden["rejectedClaims"])
        self.assertIn("p114-evidence", hidden["preservedResults"])
        weights = evaluate(payload(
            frames=[{"origin": "captured", "weight": 0.4, "synthesized": False, "confidence": 1.0}],
        ))
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-patterns"
        result = evaluate(payload(evidenceId=evidence, repeat="repetitive patterns"))
        self.assert_contract(result, evidence)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(
                frames=[{"origin": "estimated", "weight": 1.0, "synthesized": False, "confidence": 1.0}],
                contains_estimated=True,
            ))
