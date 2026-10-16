"""Tests for TC-P114-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "integer",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [{"origin": "captured", "weight": 1.0}],
        "displayed_angle_degrees": 180.0,
        "applied_exposure_seconds": (180.0 / 360.0) / 24.0,
        "sensor_max_exposure_seconds": 1.0,
        "output_fps": 24.0,
        "low_light_automatic": False,
    }
    base.update(overrides)
    return base


class TCP11401(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Shutter feasibility mismatch")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A displayed angle must not conceal a different applied exposure.",
        )

    def test_integer_rate_feasible_setting_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_fractional_rate_keeps_the_named_angle(self):
        fps = 24000 / 1001
        result = evaluate(payload(
            repeat="fractional",
            fps=fps,
            output_fps=fps,
            applied_exposure_seconds=(180.0 / 360.0) / fps,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_sensor_limit_is_shown_instead_of_the_requested_angle(self):
        result = evaluate(payload(
            displayed_angle_degrees=43.2,
            applied_exposure_seconds=0.005,
            sensor_max_exposure_seconds=0.005,
            low_light_automatic=True,
            repeat="low-light",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_displayed_angle_that_conceals_applied_exposure_is_rejected(self):
        result = evaluate(payload(
            displayed_angle_degrees=180.0,
            applied_exposure_seconds=0.005,
            sensor_max_exposure_seconds=0.005,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("displayed-angle-conceals-different-applied-exposure", result["rejectedClaims"])

    def test_cadence_change_is_rejected(self):
        result = evaluate(payload(output_fps=12.0, low_light_automatic=True, repeat="low-light"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("source-cadence-silently-changed", result["rejectedClaims"])

    def test_hidden_estimate_unnormalized_weight_and_sensor_label_are_rejected(self):
        hidden = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0}],
            contains_estimated=True,
            disclosed=False,
        ))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("hidden-hallucination", hidden["rejectedClaims"])
        self.assertIn("p114-evidence", hidden["preservedResults"])
        weights = evaluate(payload(frames=[{"origin": "captured", "weight": 0.25}]))
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])
        missing = evaluate(payload(fps=None))
        self.assertIn("missing-fps", missing["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-fractional"
        result = evaluate(payload(evidenceId=evidence, repeat="fractional"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[{"origin": "guessed", "weight": 1.0}]))
