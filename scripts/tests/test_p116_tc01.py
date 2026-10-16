"""Tests for TC-P116-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p116_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p116_tc01.py",
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
        "withheldMidpoint": {"time": 0.5, "value": 1.0},
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p116-evidence",
        "repeat": "Repeat",
        "frameRate": 24.0,
        "outputFrameRate": 24.0,
        "shutterAngleDegrees": 180.0,
        "displayedShutterAngleDegrees": 180.0,
        "appliedExposureSeconds": (180.0 / 360.0) / 24.0,
        "sensorMinExposureSeconds": 0.000125,
        "sensorMaxExposureSeconds": 1.0 / 24.0,
    }
    base.update(timeline())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP11601(unittest.TestCase):
    def assert_contract(self, result, evidence="p116-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P116-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("interpolationFraction=1/3=0.3333333333333333", blob(result))
        self.assertTrue(result["reasons"])

    def test_feasible_shutter_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

    def test_displayed_angle_concealing_exposure_is_rejected(self):
        result = evaluate(payload(displayedShutterAngleDegrees=90.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p116-evidence", result["preservedResults"])

    def test_hidden_hallucination_is_rejected(self):
        result = evaluate(payload(**timeline(
            estimated=[{"time": 0.5, "value": 1.0, "origin": "captured"}],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-hallucination", result["rejectedClaims"])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

    def test_infeasible_request_can_keep_an_honest_feasible_angle(self):
        feasible = (180.0 / 360.0) / 24.0
        result = evaluate(payload(
            shutterAngleDegrees=360.0,
            displayedShutterAngleDegrees=180.0,
            appliedExposureSeconds=feasible,
            sensorMaxExposureSeconds=feasible,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("effectiveFeasibleShutterAngleDegrees=" in item for item in result["reasons"]))

    def test_silent_cadence_change_is_rejected(self):
        result = evaluate(payload(outputFrameRate=12.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p116-fractional"
        result = evaluate(payload(evidenceId=evidence, repeat="fractional", frameRate=23.976, outputFrameRate=23.976,
                                  appliedExposureSeconds=(180.0 / 360.0) / 23.976))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
