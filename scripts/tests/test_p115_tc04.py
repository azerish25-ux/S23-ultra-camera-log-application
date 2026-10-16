"""Tests for TC-P115-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p115_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p115_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frame(origin="synthesized", marked=True, confidence=0.9):
    return {"origin": origin, "markedSynthesized": marked, "occlusionConfidence": confidence}


def payload(**overrides):
    base = {
        "evidenceId": "p115-occlusion",
        "frames": [frame("sensor", False, 0.95), frame("synthesized", True, 0.8)],
        "policy": "bounded",
        "confidenceFloor": 0.5,
        "repeat": "reflective",
    }
    base.update(overrides)
    return base


class TCP11504(unittest.TestCase):
    def assert_contract(self, result, evidence="p115-occlusion"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P115-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Interpolation occlusion artifact")
        self.assertEqual(_MODULE.NEGATIVE, "Calling interpolated frames native sensor samples must fail.")
        self.assertIn("thin fast structures", _MODULE.REPEAT)

    def test_marked_synthesized_frame_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2][1]["origin"], "synthesized")
        self.assertTrue(result["preservedResults"][2][1]["markedSynthesized"])

    def test_unmarked_interpolation_is_rejected(self):
        result = evaluate(
            payload(
                frames=[frame("synthesized", False, 0.9)],
                repeat="repetitive-pattern",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("interpolated-called-native", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertFalse(result["preservedResults"][2][0]["markedSynthesized"])

    def test_low_confidence_fallback_is_recorded_and_integrate_anyway_is_rejected(self):
        recorded = evaluate(
            payload(
                evidenceId="p115-fallback",
                frames=[frame("synthesized", True, 0.2)],
                policy="fallback",
                repeat="thin-fast",
            )
        )
        self.assert_contract(recorded, "p115-fallback")
        self.assertEqual(recorded["decision"], "recorded")
        rejected = evaluate(
            payload(frames=[frame("sensor", False, 0.2)], policy="integrate-anyway")
        )
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("occlusion-unbounded", rejected["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[frame("sensor", True, 0.9)]))
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[frame("guess", False, 0.9)]))
