"""Tests for TC-P116-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p116_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p116_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def timeline(**overrides):
    value = {
        "captured": [
            {"time": 0.0, "value": 0.0, "origin": "captured"},
            {"time": 1.0, "value": 2.0, "origin": "captured"},
        ],
        "estimated": [{"time": 0.5, "value": 1.0, "origin": "estimated"}],
        "withheldMidpoint": {"time": 0.5, "value": 4.0},
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p116-evidence",
        "repeat": "Repeat",
        "confidence": 0.9,
        "confidenceFloor": 0.5,
        "occlusionPresent": False,
        "artifactScore": 0.1,
        "artifactBound": 0.4,
        "fallbackApplied": False,
    }
    base.update(timeline())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP11604(unittest.TestCase):
    def assert_contract(self, result, evidence="p116-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P116-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("interpolationFraction=1/3=0.3333333333333333", blob(result))

    def test_bounded_interpolation_is_recorded_as_estimated(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])
        self.assertIn("withheldMidpointResidual=3", blob(result))
        self.assertIn("residual does not relabel estimated samples as captured", result["reasons"])

    def test_native_sensor_label_is_rejected(self):
        result = evaluate(payload(**timeline(
            estimated=[{"time": 0.5, "value": 1.0, "origin": "captured"}],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("hidden-hallucination", result["rejectedClaims"])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

    def test_low_confidence_without_fallback_is_rejected(self):
        result = evaluate(payload(confidence=0.2, occlusionPresent=True, artifactScore=0.9))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOW_CONFIDENCE, result["rejectedClaims"])
        self.assertIn(_MODULE.UNBOUNDED, result["rejectedClaims"])

    def test_fallback_keeps_estimated_origin(self):
        result = evaluate(payload(confidence=0.2, occlusionPresent=True, artifactScore=0.9, fallbackApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])
        self.assertTrue(any("fallback retains origin=estimated" in item for item in result["reasons"]))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p116-specular"
        result = evaluate(payload(evidenceId=evidence, repeat="reflective"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
