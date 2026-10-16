"""Tests for TC-P113-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "constant-velocity",
        "domain": "linear",
        "samples": [0, 1],
        "weights": ["1/2", "1/2"],
        "normalized": True,
        "velocity": 48,
        "acceleration": 0,
        "shutterAngleDegrees": 180,
        "fps": 24,
        "independentEnergy": "1/2",
        "trailExtent": 1,
        "overlap": None,
        "sensorConfirmed": False,
        "measurementId": None,
        "syntheticIntegration": False,
    }
    base.update(overrides)
    return base


class TCP11303(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constant_velocity_matches_linear_energy_and_trail(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        self.assertIn("trail extent 1", result["reasons"])

    def test_display_encoding_and_unnormalized_weights_fail(self):
        display = evaluate(payload(domain="display"))
        self.assert_contract(display)
        self.assertEqual(display["decision"], "rejected")
        self.assertIn("display-encoded-or-unnormalized-weights", display["rejectedClaims"])
        self.assertIn("display-encoded-temporal-average", display["rejectedClaims"])
        weights = evaluate(payload(normalized=False, weights=[1, 1], independentEnergy="1/2"))
        self.assertEqual(weights["decision"], "rejected")
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])

    def test_acceleration_and_partial_boundary_use_the_exposure_window(self):
        accelerated = evaluate(payload(
            repeat="acceleration",
            velocity=0,
            acceleration=48,
            trailExtent="1/96",
        ))
        self.assertEqual(accelerated["decision"], "recorded")
        self.assertIn("trail extent 1/96", accelerated["reasons"])
        partial = evaluate(payload(
            repeat="partial-boundary",
            overlap="1/2",
            independentEnergy="1/4",
            trailExtent="1/2",
        ))
        self.assertEqual(partial["decision"], "recorded")
        self.assertIn("trail extent 1/2", partial["reasons"])

    def test_trail_mismatch_is_rejected(self):
        result = evaluate(payload(trailExtent=2))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("energy-or-trail-mismatch", result["rejectedClaims"])
        self.assertIn("p113-evidence", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(shutterAngleDegrees=-5))
        with self.assertRaises(ValueError):
            evaluate(payload(samples=[float("nan"), 1]))
