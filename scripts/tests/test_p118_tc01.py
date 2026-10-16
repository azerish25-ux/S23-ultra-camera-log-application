"""Tests for TC-P118-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def correction(**overrides):
    value = {
        "readoutSecondsPerRow": None,
        "readoutSource": None,
        "cameraVelocityY": 0.0,
        "warpLabel": "none",
        "claimsGlobalShutterRestored": False,
        "rows": [{"rowIndex": 0, "y": 1.0, "velocityY": 0.0, "role": "background"}],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    rate = 24.0
    implied = (180.0 / 360.0) / rate
    base = {
        "evidenceId": "p118-shutter",
        "repeat": "integer-frame-rate",
        "displayedAngle": 180.0,
        "appliedExposure": implied,
        "sensorTimingExposure": implied,
        "exposureLimit": 1.0 / 24.0,
        "sourceCadence": rate,
        "outputCadence": rate,
    }
    base.update(correction())
    base.update(overrides)
    return base


class TCP11801(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-shutter"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

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
        self.assertIn("correction_applied false", result["preservedResults"])
        details = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(details["sourceCadence"], 24.0)
        self.assertEqual(details["outputCadence"], 24.0)
        self.assertAlmostEqual(details["feasibleExposure"], (180.0 / 360.0) / 24.0)

    def test_concealed_exposure_is_rejected_without_rewriting_cadence(self):
        result = evaluate(payload(appliedExposure=0.01, repeat="low-light-automatic"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        details = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(details["sourceCadence"], 24.0)
        self.assertEqual(details["outputCadence"], 24.0)
        self.assertEqual(details["appliedExposure"], 0.01)

    def test_fractional_frame_rate_can_be_recorded(self):
        rate = 23.976
        implied = (180.0 / 360.0) / rate
        result = evaluate(
            payload(
                evidenceId="p118-fractional",
                sourceCadence=rate,
                outputCadence=rate,
                appliedExposure=implied,
                sensorTimingExposure=implied,
                exposureLimit=1.0 / rate,
                repeat="fractional-frame-rate",
            )
        )
        self.assert_contract(result, "p118-fractional")
        self.assertEqual(result["decision"], "recorded")

    def test_cadence_change_and_exposure_limit_are_rejected(self):
        implied = (180.0 / 360.0) / 24.0
        result = evaluate(
            payload(
                outputCadence=30.0,
                exposureLimit=0.01,
                sensorTimingExposure=0.01,
                appliedExposure=implied,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.LIMIT_TOKEN, result["rejectedClaims"])
        details = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(details["sourceCadence"], 24.0)
        self.assertEqual(details["outputCadence"], 30.0)
        self.assertEqual(details["feasibleExposure"], 0.01)

    def test_unknown_readout_warp_does_not_shift_rows(self):
        result = evaluate(
            payload(
                **correction(
                    warpLabel="rolling_shutter_correction",
                    rows=[{"rowIndex": 2, "y": 5.0, "velocityY": 8.0, "role": "background"}],
                )
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("rolling-shutter-correction-without-measured-readout", result["rejectedClaims"])
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertIn([5.0], result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [5.0])
        self.assertEqual(result["preservedResults"][5], [0.0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(displayedAngle=400))
        with self.assertRaises(ValueError):
            evaluate(payload(sourceCadence=0))
