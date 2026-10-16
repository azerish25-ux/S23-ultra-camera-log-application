"""Tests for TC-P117-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc04.py",
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
        "evidenceId": "p117-occlusion",
        "repeat": "reflective-objects",
        "confidence": 0.9,
        "confidenceFloor": 0.5,
        "occlusionPresent": True,
        "artifactScore": 0.2,
        "artifactBound": 0.5,
        "fallbackApplied": False,
        "frames": [
            {"synthesized": False, "origin": "captured"},
            {"synthesized": True, "origin": "estimated"},
        ],
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11704(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-occlusion"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Interpolation occlusion artifact")
        self.assertEqual(_MODULE.NEGATIVE, "Calling interpolated frames native sensor samples must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat reflective objects, repetitive patterns, and thin fast structures.",
        )

    def test_estimated_intermediate_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frame[1] origin=estimated synthesized=yes", result["preservedResults"])

    def test_native_label_on_a_synthesized_frame_is_rejected(self):
        result = evaluate(payload(frames=[
            {"synthesized": True, "origin": "captured"},
        ]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_low_confidence_without_fallback_is_rejected(self):
        result = evaluate(payload(confidence=0.2, repeat="repetitive-patterns"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOW_CONFIDENCE, result["rejectedClaims"])

    def test_unbounded_occlusion_is_rejected(self):
        result = evaluate(payload(artifactScore=0.9, repeat="thin-fast-structures"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNBOUNDED, result["rejectedClaims"])

    def test_fallback_keeps_synthesized_frames_estimated(self):
        result = evaluate(payload(confidence=0.2, artifactScore=0.9, fallbackApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("frame[1] origin=estimated synthesized=yes", result["preservedResults"])

    def test_dropped_lens_is_rejected_with_clean_frames(self):
        geo = geometry()
        geo["stabilized"] = {"lensId": "other-lens", "timestamp": 0.0, "aspect": 1.5}
        result = evaluate(payload(geometry=geo))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dropped-lens-identity", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
