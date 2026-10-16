"""Tests for TC-P120-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def honest_report(**overrides):
    value = {
        "shutter_angle": 180.0,
        "fps": 1.0,
        "exposure_seconds": 0.5,
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
        "domain": "linear",
        "weights": [0.25, 0.25, 0.5],
        "linearValues": [1.0, 1.0, 3.0],
        "referenceEnergy": 2.0,
        "velocity": 4.0,
        "acceleration": 2.0,
        "exposureWindow": 0.5,
        "reportedTrailExtent": 2.25,
        "partialBoundary": False,
    }
    base.update(overrides)
    return base


class TCP12003(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("integratedEnergy=") for item in result["preservedResults"]))

    def test_linear_energy_and_trail_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("integratedEnergy=2", result["reasons"])
        self.assertIn("trailExtent=2.25", result["reasons"])

    def test_display_encoded_average_is_rejected(self):
        result = evaluate(payload(domain="display"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unnormalized_weights_are_rejected(self):
        result = evaluate(payload(weights=[0.5, 0.5, 0.5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNNORMALIZED_TOKEN, result["rejectedClaims"])

    def test_energy_mismatch_is_rejected(self):
        result = evaluate(payload(referenceEnergy=9.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ENERGY_TOKEN, result["rejectedClaims"])

    def test_window_that_disagrees_with_the_report_is_rejected(self):
        result = evaluate(payload(exposureWindow=0.25, reportedTrailExtent=1.0625))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WINDOW_TOKEN, result["rejectedClaims"])

    def test_partial_boundary_stays_recorded_when_the_window_matches(self):
        result = evaluate(payload(partialBoundary=True, repeat="partial exposure"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("partial boundary" in item for item in result["reasons"]))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-accel"
        result = evaluate(payload(evidenceId=evidence, repeat="acceleration"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
