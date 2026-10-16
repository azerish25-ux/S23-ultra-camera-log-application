"""Tests for TC-P113-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "integer-frame-rate",
        "shutterAngleDegrees": 180,
        "fps": 24,
        "sensorIntervalSeconds": None,
        "syntheticIntegration": False,
        "displayedAngleDegrees": 180,
        "appliedExposureSeconds": "1/48",
        "sourceCadenceFps": 24,
        "sensorConfirmed": False,
        "measurementId": None,
        "automaticShutterRewrite": False,
        "lightLimitSeconds": None,
    }
    base.update(overrides)
    return base


class TCP11301(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_module_encodes_the_case_contract(self):
        self.assertEqual(_MODULE.NAME, "Shutter feasibility mismatch")
        self.assertIn("sensor timing", _MODULE.INTERVENTION)
        self.assertIn("source cadence", _MODULE.EXPECTED)
        self.assertIn("displayed angle", _MODULE.NEGATIVE)
        self.assertIn("fractional", _MODULE.REPEAT)

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("requested-angle-degrees:180", result["preservedResults"])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        self.assertIn("180 deg at 24 fps = 1/48 s", result["reasons"])
        self.assertIn("no sensor-angle claim is made", " ".join(result["reasons"]))

    def test_displayed_angle_cannot_conceal_a_different_exposure(self):
        result = evaluate(payload(appliedExposureSeconds="1/96"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("displayed-angle-conceals-applied-exposure", result["rejectedClaims"])
        self.assertIn("angle-exposure-inconsistency", result["rejectedClaims"])

    def test_exposure_past_the_sensor_interval_is_rejected_without_a_cadence_change(self):
        result = evaluate(payload(
            appliedExposureSeconds="1/12",
            sensorIntervalSeconds="1/24",
            syntheticIntegration=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exposure-exceeds-frame-interval", result["rejectedClaims"])
        self.assertIn("source-cadence-fps:24", result["preservedResults"])

    def test_fractional_frame_rate_and_low_light_repeat(self):
        fractional = evaluate(payload(
            repeat="fractional-frame-rate",
            fps={"numerator": 24000, "denominator": 1001},
            sourceCadenceFps={"numerator": 24000, "denominator": 1001},
            appliedExposureSeconds={"numerator": 1001, "denominator": 48000},
        ))
        self.assertEqual(fractional["decision"], "recorded")
        self.assertIn("effective-exposure-seconds:1001/48000", fractional["preservedResults"])
        limited = evaluate(payload(
            repeat="low-light-automatic",
            lightLimitSeconds="1/96",
        ))
        self.assertEqual(limited["decision"], "rejected")
        self.assertIn("exposure-exceeds-sensor-limit", limited["rejectedClaims"])
        self.assertIn("source-cadence-fps:24", limited["preservedResults"])
        rewritten = evaluate(payload(repeat="low-light-automatic", automaticShutterRewrite=True))
        self.assertEqual(rewritten["decision"], "rejected")
        self.assertIn("low-light-automatic-shutter-change", rewritten["rejectedClaims"])

    def test_angle_above_360_is_rejected(self):
        exposure = _MODULE._CORE.exposure_seconds(400, 24)
        result = evaluate(payload(
            shutterAngleDegrees=400,
            displayedAngleDegrees=400,
            appliedExposureSeconds=_MODULE._CORE.format_number(exposure),
            syntheticIntegration=True,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("angle-above-360", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p113-with"
        result = evaluate(payload(evidenceId=evidence, repeat="fractional-frame-rate"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_sensor_confirmation_without_a_measurement_is_rejected(self):
        result = evaluate(payload(sensorConfirmed=True, measurementId=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sensor-confirmed-without-measurement-id", result["rejectedClaims"])
        confirmed = evaluate(payload(sensorConfirmed=True, measurementId="meas-p113-01"))
        self.assertEqual(confirmed["decision"], "recorded")
        self.assertIn("measurement-id:meas-p113-01", confirmed["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(shutterAngleDegrees=0))
        with self.assertRaises(ValueError):
            evaluate(payload(fps=0))
        with self.assertRaises(ValueError):
            evaluate(payload(fps=float("nan")))
        with self.assertRaises(ValueError):
            evaluate(payload(shutterAngleDegrees=float("-inf")))
