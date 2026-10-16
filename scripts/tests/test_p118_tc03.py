"""Tests for TC-P118-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc03.py",
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
    weights = [0.25, 0.5, 0.25]
    values = [0.0, 4.0, 0.0]
    window = 0.5
    velocity = 2.0
    acceleration = 0.0
    base = {
        "evidenceId": "p118-energy",
        "repeat": "constant-velocity",
        "domain": "linear",
        "weights": weights,
        "linearValues": values,
        "referenceEnergy": 2.0,
        "velocity": velocity,
        "acceleration": acceleration,
        "exposureWindow": window,
        "reportedTrailExtent": abs(velocity) * window,
        "partialBoundary": False,
    }
    base.update(correction())
    base.update(overrides)
    return base


class TCP11803(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-energy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Temporal integration energy")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Averaging display-encoded frames or unnormalized temporal weights must fail.",
        )

    def test_linear_energy_and_trail_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("integratedEnergy=2", result["reasons"])
        self.assertIn("trailExtent=1", result["reasons"])
        self.assertEqual(result["preservedResults"][7], 2.0)
        self.assertEqual(result["preservedResults"][8], 1.0)

    def test_acceleration_trail_uses_half_window_squared(self):
        window = 2.0
        result = evaluate(
            payload(
                repeat="acceleration",
                velocity=1.0,
                acceleration=4.0,
                exposureWindow=window,
                reportedTrailExtent=1.0 * window + 0.5 * 4.0 * window * window,
                partialBoundary=True,
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][8], 10.0)
        self.assertIn("partial boundary uses the supplied exposure window only", result["reasons"])

    def test_display_average_and_unnormalized_weights_are_rejected(self):
        display = evaluate(payload(domain="display"))
        self.assertEqual(display["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, display["rejectedClaims"])
        weights = evaluate(payload(weights=[0.5, 0.5, 0.5], referenceEnergy=3.0))
        self.assertEqual(weights["decision"], "rejected")
        self.assertIn(_MODULE.UNNORMALIZED_TOKEN, weights["rejectedClaims"])
        negative = evaluate(payload(weights=[-0.25, 0.75, 0.5], referenceEnergy=2.75, linearValues=[1.0, 4.0, 0.0]))
        self.assertEqual(negative["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_WEIGHT, negative["rejectedClaims"])
        self.assertEqual(negative["preservedResults"][6], [-0.25, 0.75, 0.5])

    def test_trail_mismatch_is_rejected(self):
        result = evaluate(payload(reportedTrailExtent=9.0))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ENERGY_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][8], 1.0)

    def test_unknown_readout_warp_does_not_shift_rows(self):
        result = evaluate(
            payload(
                **correction(
                    warpLabel="rolling_shutter_correction",
                    rows=[{"rowIndex": 4, "y": 3.0, "velocityY": 5.0, "role": "background"}],
                )
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [3.0])
        self.assertEqual(result["preservedResults"][5], [0.0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(weights=[0.5], linearValues=[1.0, 2.0]))
