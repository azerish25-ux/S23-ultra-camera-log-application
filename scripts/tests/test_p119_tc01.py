"""Tests for TC-P119-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p119_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p119_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _limit(limit_id="mode-24", fps=24.0, shutter=180.0):
    return {
        "id": limit_id,
        "fps": fps,
        "shutter_angle": shutter,
        "max_stable_motion_px": 8.0,
        "mode_available": True,
    }


def _statement(limit_id="mode-24", text="displayed shutter matches the applied exposure", **overrides):
    value = {
        "text": text,
        "limitId": limit_id,
        "recommendsFps": None,
        "recommendsShutter": None,
        "observedMotionPx": 1.0,
        "claimsStableMotion": True,
        "promises": [],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p119-shutter",
        "displayedAngle": 180,
        "appliedExposure": 0.5,
        "sensorTimingExposure": 0.5,
        "exposureLimit": 1.0,
        "sourceCadence": 24,
        "outputCadence": 24,
        "repeat": "integer-frame-rate",
        "selectedLimitId": "mode-24",
        "measuredLimits": [_limit()],
        "guidance": [_statement()],
    }
    base.update(overrides)
    return base


class TCP11901(unittest.TestCase):
    def assert_contract(self, result, evidence="p119-shutter"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P119-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

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
        kept = result["preservedResults"][1]
        self.assertEqual(kept["feasibleExposure"], 0.5)
        self.assertEqual(kept["sourceCadence"], 24.0)
        self.assertEqual(kept["outputCadence"], 24.0)

    def test_concealed_exposure_is_rejected_without_rewriting_cadence(self):
        result = evaluate(payload(appliedExposure=0.25, repeat="low-light-automatic"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("displayed-angle-conceals-applied-exposure", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["sourceCadence"], 24.0)
        self.assertEqual(kept["outputCadence"], 24.0)
        self.assertEqual(kept["feasibleExposure"], 0.5)
        self.assertEqual(kept["appliedExposure"], 0.25)

    def test_fractional_frame_rate_can_be_recorded(self):
        result = evaluate(
            payload(
                evidenceId="p119-fractional",
                sourceCadence=23.976,
                outputCadence=23.976,
                repeat="fractional-frame-rate",
            )
        )
        self.assert_contract(result, "p119-fractional")
        self.assertEqual(result["decision"], "recorded")

    def test_honest_limit_below_180_is_recorded(self):
        shown = 172.8
        implied = shown / 360.0
        result = evaluate(
            payload(
                evidenceId="p119-feasible",
                displayedAngle=shown,
                appliedExposure=implied,
                sensorTimingExposure=implied,
                sourceCadence=48,
                outputCadence=48,
                selectedLimitId="mode-48",
                measuredLimits=[_limit("mode-48", 48.0, 172.8)],
                guidance=[
                    _statement(
                        "mode-48",
                        "this mode cannot do 180 degrees at this fps",
                    )
                ],
            )
        )
        self.assert_contract(result, "p119-feasible")
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("honest-180:" in item for item in result["reasons"]))
        self.assertEqual(result["preservedResults"][1]["sourceCadence"], 48.0)
        self.assertEqual(result["preservedResults"][1]["outputCadence"], 48.0)

    def test_unsupported_shutter_recommendation_is_rejected(self):
        result = evaluate(
            payload(
                selectedLimitId="mode-48",
                sourceCadence=48,
                outputCadence=48,
                measuredLimits=[_limit("mode-48", 48.0, 172.8)],
                guidance=[_statement("mode-48", "set the shutter to 180 degrees", recommendsShutter=180.0)],
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-shutter", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["sourceCadence"], 48.0)

    def test_cadence_change_and_exposure_limit_are_rejected(self):
        result = evaluate(payload(outputCadence=30, exposureLimit=0.4, sensorTimingExposure=0.4, appliedExposure=0.5))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("source-cadence-changed", result["rejectedClaims"])
        self.assertIn("exposure-limit", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["sourceCadence"], 24.0)
        self.assertEqual(result["preservedResults"][1]["feasibleExposure"], 0.4)

    def test_ungrounded_guidance_is_rejected(self):
        result = evaluate(payload(guidance=[_statement(text="raise the shutter to 180 degrees", limitId=None)]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("ungrounded-guidance", result["rejectedClaims"])
        self.assertIn("p119-shutter", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(displayedAngle=400))
        with self.assertRaises(ValueError):
            evaluate(payload(sourceCadence=23.976))
