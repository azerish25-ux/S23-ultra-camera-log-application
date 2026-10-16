"""Host checks for P113. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import unittest
from fractions import Fraction
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_implement_shutter_angle_controls_correctly",
    Path(__file__).resolve().parents[1] / "gates" / "p113_implement_shutter_angle_controls_correctly.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE = _ROOT / "docs" / "P113_IMPLEMENT_SHUTTER_ANGLE_CONTROLS_CORRECTLY.json"
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def document(**overrides):
    value = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    value.update(overrides)
    return value


def request(**overrides):
    value = {
        "evidenceId": "p113-shutter-180-at-24",
        "shutterAngleDegrees": 180,
        "fps": 24,
        "reportedAngleDegrees": 180,
        "reportedExposureSeconds": "1/48",
        "sourceCadenceFps": 24,
        "syntheticIntegration": False,
        "sensorConfirmed": False,
        "measurementId": None,
        "reportsAngleAsApplied": True,
    }
    value.update(overrides)
    return value


class P113Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-shutter-180-at-24"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P113")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants_match_the_spec(self):
        self.assertEqual(BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(
            _MODULE.GOAL,
            "Translate creative shutter angle into a feasible physical exposure request.",
        )
        self.assertEqual(_MODULE.MUTANT, "Treat shutter angle as an arbitrary blur-strength percentage.")
        self.assertEqual(_MODULE.DELIVERABLE, "Shutter-angle model and exposure feasibility tests")

    def test_exposure_formula_is_one_forty_eighth_at_180_degrees_24_fps(self):
        exposure = _MODULE.exposure_seconds(180, 24)
        interval = _MODULE.frame_interval_seconds(24)
        self.assertEqual(exposure, Fraction(1, 48))
        self.assertEqual(interval, Fraction(1, 24))
        self.assertLess(exposure, interval)
        self.assertEqual(_MODULE.exposure_seconds(180, Fraction(24000, 1001)), Fraction(1001, 48000))

    def test_authored_fixture_is_recorded_not_qualified(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("requested-angle-degrees:180", result["preservedResults"])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertIn("180 deg at 24 fps = 1/48 s", result["reasons"])
        text = " ".join(result["reasons"])
        self.assertIn("no sensor-angle claim is made", text)
        self.assertNotIn("sensor used the shutter angle", text)
        self.assertIn("exposure-exceeds-frame-interval", text)

    def test_evaluate_accepts_the_same_fixture(self):
        self.assertEqual(evaluate(document())["decision"], "recorded")

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])

    def test_blur_percentage_interpretation_is_rejected(self):
        result = evaluate(request(blurPercentInterpretation=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("formula-exposure-seconds:1/48", result["preservedResults"])

    def test_angle_above_360_is_rejected_even_when_synthetic(self):
        result = evaluate(request(
            shutterAngleDegrees=361,
            reportedAngleDegrees=None,
            reportedExposureSeconds=None,
            reportsAngleAsApplied=False,
            syntheticIntegration=True,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("angle-above-360", result["rejectedClaims"])
        self.assertIn("p113-shutter-180-at-24", result["preservedResults"])

    def test_full_open_shutter_matches_the_frame_interval(self):
        result = evaluate(request(
            shutterAngleDegrees=360,
            reportedAngleDegrees=360,
            reportedExposureSeconds="1/24",
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("effective-exposure-seconds:1/24", result["preservedResults"])
        self.assertIn("requested-angle-degrees:360", result["preservedResults"])

    def test_exposure_longer_than_the_frame_is_rejected_without_synthetic_integration(self):
        result = evaluate(request(
            requestedExposureSeconds="1/12",
            reportedAngleDegrees=None,
            reportedExposureSeconds=None,
            reportsAngleAsApplied=False,
            syntheticIntegration=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exposure-exceeds-frame-interval", result["rejectedClaims"])
        self.assertIn("source-cadence-fps:24", result["preservedResults"])
        self.assertIn("requested-angle-degrees:180", result["preservedResults"])
        self.assertIn("effective-exposure-seconds:1/12", result["preservedResults"])

    def test_synthetic_integration_must_be_explicitly_true(self):
        result = evaluate(request(
            requestedExposureSeconds="1/12",
            reportedAngleDegrees=None,
            reportedExposureSeconds=None,
            reportsAngleAsApplied=False,
            syntheticIntegration=True,
        ))
        self.assertEqual(result["decision"], "recorded")
        text = " ".join(result["reasons"])
        self.assertIn("synthetic_integration is true", text)
        self.assertIn("not the applied shutter", text)
        self.assertNotIn("sensor used the shutter angle", text)

    def test_reporting_180_with_a_different_duration_is_rejected(self):
        result = evaluate(request(reportedExposureSeconds="1/50"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("angle-exposure-inconsistency", result["rejectedClaims"])
        self.assertIn("requested-angle-degrees:180", result["preservedResults"])

    def test_sensor_confirmation_requires_a_measurement_id(self):
        rejected = evaluate(request(sensorConfirmed=True, measurementId=None))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("sensor-confirmed-without-measurement-id", rejected["rejectedClaims"])
        recorded = evaluate(request(sensorConfirmed=True, measurementId="meas-180-24"))
        self.assertEqual(recorded["decision"], "recorded")
        self.assertNotIn(recorded["decision"], {"qualified", "allowed"})
        self.assertIn("measurement-id:meas-180-24", recorded["preservedResults"])
        self.assertIn("sensor used the shutter angle only as recorded by measurement meas-180-24", recorded["reasons"])

    def test_fractional_frame_rate_uses_the_same_formula(self):
        result = evaluate(request(
            fps={"numerator": 24000, "denominator": 1001},
            sourceCadenceFps={"numerator": 24000, "denominator": 1001},
            reportedAngleDegrees=180,
            reportedExposureSeconds={"numerator": 1001, "denominator": 48000},
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("effective-exposure-seconds:1001/48000", result["preservedResults"])

    def test_non_physical_numbers_raise(self):
        for angle, fps in ((0, 24), (-10, 24), (180, 0), (180, -3), (True, 24), (180, True)):
            with self.assertRaises(ValueError):
                _MODULE.exposure_seconds(angle, fps)
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                evaluate(request(fps=bad))
            with self.assertRaises(ValueError):
                evaluate(request(shutterAngleDegrees=bad))
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(request(syntheticIntegration="true"))

    def test_snake_case_aliases_follow_the_same_rules(self):
        result = evaluate({
            "evidence_id": "p113-snake",
            "shutter_angle_degrees": 180,
            "fps": 24,
            "sensor_confirmed": False,
        })
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p113-snake", result["preservedResults"])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        self.assertTrue(math.isfinite(float(_MODULE.exposure_seconds(180, 24))))
