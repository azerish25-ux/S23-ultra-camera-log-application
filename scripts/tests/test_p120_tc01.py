"""Tests for TC-P120-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def honest_report(**overrides):
    value = {
        "shutter_angle": 180.0,
        "fps": 24.0,
        "exposure_seconds": (180.0 / 360.0) / 24.0,
        "interpolation_fraction": 0.0,
        "estimated_disclosed": False,
        "stabilization_crop_fraction": 0.0,
        "rolling_shutter_readout": "unknown",
        "correction_applied": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p120-evidence",
        "repeat": "Repeat",
        "combinationPassed": True,
        "report": honest_report(),
        "frameRate": 24.0,
        "outputFrameRate": 24.0,
        "requestedShutterAngleDegrees": 180.0,
        "sensorMinExposureSeconds": 0.000125,
        "sensorMaxExposureSeconds": 1.0 / 24.0,
    }
    base.update(overrides)
    return base


class TCP12001(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_feasible_shutter_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("exposure_seconds=0.0208333333333=(shutter_angle/360)/fps", result["reasons"])

    def test_displayed_angle_concealing_a_different_exposure_is_rejected(self):
        result = evaluate(payload(
            requestedShutterAngleDegrees=180.0,
            report=honest_report(shutter_angle=90.0, exposure_seconds=(90.0 / 360.0) / 24.0),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p120-evidence", result["preservedResults"])

    def test_formula_mismatch_is_rejected(self):
        result = evaluate(payload(report=honest_report(exposure_seconds=0.04)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exposure-seconds-does-not-match-shutter-formula", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_infeasible_request_can_keep_an_honest_feasible_angle(self):
        feasible = (180.0 / 360.0) / 24.0
        result = evaluate(payload(
            requestedShutterAngleDegrees=360.0,
            sensorMaxExposureSeconds=feasible,
            report=honest_report(exposure_seconds=feasible),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any(item.startswith("effectiveFeasibleShutterAngleDegrees=") for item in result["reasons"]))

    def test_silent_cadence_change_is_rejected(self):
        result = evaluate(payload(outputFrameRate=12.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])

    def test_shutter_only_spot_check_is_rejected(self):
        result = evaluate(payload(combinationPassed=True, report={"shutter_angle": 180.0}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("shutter-only-spot-check-claimed-combination-passed", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-fractional"
        rate = 23.976
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="fractional",
            frameRate=rate,
            outputFrameRate=rate,
            report=honest_report(fps=rate, exposure_seconds=(180.0 / 360.0) / rate),
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
