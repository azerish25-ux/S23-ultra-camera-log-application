"""Tests for TC-P117-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc01.py",
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
    applied = _MODULE.exposure_seconds(180.0, 24.0)
    base = {
        "evidenceId": "p117-shutter",
        "repeat": "integer-frame-rate",
        "frameRate": 24.0,
        "outputFrameRate": 24.0,
        "shutterAngleDegrees": 180.0,
        "displayedShutterAngleDegrees": 180.0,
        "appliedExposureSeconds": applied,
        "sensorMinExposureSeconds": 0.001,
        "sensorMaxExposureSeconds": 0.05,
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11701(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-shutter"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Shutter feasibility mismatch")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Request a shutter angle whose implied exposure conflicts with actual sensor timing or exposure limits.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Show the effective feasible setting or reject it without silently changing source cadence.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "A displayed angle must not conceal a different applied exposure.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat integer and fractional frame rates and low-light automatic behavior.",
        )

    def test_matching_angle_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        applied = _MODULE.exposure_seconds(180.0, 24.0)
        self.assertIn("appliedExposureSeconds=" + _MODULE._CORE.format_number(applied), blob(result))

    def test_fractional_rate_uses_the_same_exposure_formula(self):
        rate = 23.976
        applied = _MODULE.exposure_seconds(180.0, rate)
        result = evaluate(payload(
            frameRate=rate,
            outputFrameRate=rate,
            appliedExposureSeconds=applied,
            repeat="fractional-frame-rate",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_concealed_exposure_is_rejected(self):
        result = evaluate(payload(appliedExposureSeconds=0.01, repeat="low-light-automatic"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_silent_cadence_change_is_rejected(self):
        result = evaluate(payload(outputFrameRate=30.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])

    def test_infeasible_request_can_show_the_feasible_angle(self):
        rate = 24.0
        feasible = _MODULE.exposure_seconds(90.0, rate)
        result = evaluate(payload(
            shutterAngleDegrees=180.0,
            displayedShutterAngleDegrees=90.0,
            appliedExposureSeconds=feasible,
            sensorMaxExposureSeconds=feasible,
            repeat="low-light-automatic",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("effectiveFeasibleShutterAngleDegrees=90", blob(result))

    def test_infeasible_request_that_still_displays_the_request_is_rejected(self):
        rate = 24.0
        feasible = _MODULE.exposure_seconds(90.0, rate)
        result = evaluate(payload(
            shutterAngleDegrees=180.0,
            displayedShutterAngleDegrees=180.0,
            appliedExposureSeconds=feasible,
            sensorMaxExposureSeconds=feasible,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.INFEASIBLE_TOKEN, result["rejectedClaims"])

    def test_generated_fill_rejects_an_otherwise_feasible_shutter(self):
        result = evaluate(payload(geometry=geometry(fill="generated")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("generated-fill", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p117-shutter-fraction"
        result = evaluate(payload(evidenceId=evidence, repeat="fractional-frame-rate"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
