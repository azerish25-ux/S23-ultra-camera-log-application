"""Tests for TC-P114-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frames(pairs, origin="captured"):
    return [
        {"origin": origin, "weight": weight, "position": position, "radiance": radiance}
        for weight, position, radiance in pairs
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "constant velocity",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": frames([(0.5, 0.0, 1.0), (0.5, 4.0, 1.0)]),
        "domain": "linear",
        "reference_energy": 1.0,
        "reference_trail": 4.0,
    }
    base.update(overrides)
    return base


class TCP11403(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_linear_energy_and_trail_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_acceleration_and_boundary_partial_exposure_match(self):
        accelerated = evaluate(payload(
            repeat="acceleration",
            frames=frames([(0.25, 0.0, 2.0), (0.75, 9.0, 2.0)]),
            reference_energy=2.0,
            reference_trail=9.0,
        ))
        self.assertEqual(accelerated["decision"], "recorded")
        boundary = evaluate(payload(
            repeat="partial exposure at clip boundaries",
            frames=frames([(0.25, 0.0, 4.0), (0.75, 2.0, 0.0)]),
            reference_energy=1.0,
            reference_trail=2.0,
        ))
        self.assertEqual(boundary["decision"], "recorded")

    def test_display_average_is_rejected_even_when_numbers_match(self):
        result = evaluate(payload(domain="display"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-encoded-frame-average", result["rejectedClaims"])
        self.assertNotIn("linear-energy-mismatch", result["rejectedClaims"])

    def test_unnormalized_weights_and_energy_or_trail_misses_are_rejected(self):
        weights = evaluate(payload(
            frames=frames([(0.4, 0.0, 1.0), (0.4, 1.0, 1.0)]),
            reference_energy=0.8,
            reference_trail=1.0,
        ))
        self.assertEqual(weights["decision"], "rejected")
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])
        self.assertNotIn("linear-energy-mismatch", weights["rejectedClaims"])
        energy = evaluate(payload(reference_energy=5.0))
        self.assertIn("linear-energy-mismatch", energy["rejectedClaims"])
        trail = evaluate(payload(reference_trail=1.0))
        self.assertIn("trail-extent-mismatch", trail["rejectedClaims"])
        self.assertIn("p114-evidence", trail["preservedResults"])

    def test_hidden_estimate_is_rejected(self):
        result = evaluate(payload(
            frames=frames([(1.0, 0.0, 1.0)], origin="estimated"),
            contains_estimated=True,
            disclosed=False,
            reference_energy=1.0,
            reference_trail=0.0,
        ))
        self.assertIn("hidden-hallucination", result["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])
        missing = evaluate(payload(fps=None))
        self.assertIn("missing-fps", missing["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-accel"
        result = evaluate(payload(evidenceId=evidence, repeat="acceleration"))
        self.assert_contract(result, evidence)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(domain="log"))
        with self.assertRaises(ValueError):
            evaluate(payload(frames=frames([(1.0, 0.0, -1.0)])))
