"""Tests for TC-P117-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def geometry(**overrides):
    value = _MODULE._CORE.recorded_geometry()
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p117-energy",
        "repeat": "constant-velocity",
        "domain": "linear",
        "weights": [0.25, 0.5, 0.25],
        "linearValues": [0.0, 4.0, 0.0],
        "velocity": 2.0,
        "acceleration": 0.0,
        "exposureStart": 0.0,
        "exposureEnd": 1.0,
        "clipStart": 0.0,
        "clipEnd": 1.0,
        "reportedEnergy": 2.0,
        "reportedTrailExtent": 2.0,
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11703(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-energy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Temporal integration energy")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Averaging display-encoded frames or unnormalized temporal weights must fail.",
        )

    def test_linear_energy_and_trail_are_recorded(self):
        self.assertEqual(_MODULE.linear_energy([0.25, 0.5, 0.25], [0.0, 4.0, 0.0]), 2.0)
        self.assertEqual(_MODULE.trail_extent(2.0, 0.0, 1.0), 2.0)
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("linearEnergy=2", result["preservedResults"])
        self.assertIn("trailExtent=2", result["preservedResults"])

    def test_acceleration_trail_uses_half_a_t_squared(self):
        extent = _MODULE.trail_extent(0.0, 4.0, 0.5)
        self.assertEqual(extent, 0.5)
        result = evaluate(payload(
            velocity=0.0,
            acceleration=4.0,
            exposureEnd=0.5,
            clipEnd=0.5,
            reportedEnergy=2.0,
            reportedTrailExtent=extent,
            repeat="acceleration",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_partial_boundary_uses_overlap_not_the_requested_window(self):
        overlap = _MODULE.overlap_duration(0.0, 2.0, 0.0, 1.0)
        self.assertEqual(overlap, 1.0)
        result = evaluate(payload(
            exposureEnd=2.0,
            clipEnd=1.0,
            reportedTrailExtent=2.0,
            repeat="partial-exposure",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("partial exposure at the clip boundary", blob(result))
        clipped = evaluate(payload(
            exposureEnd=2.0,
            clipEnd=1.0,
            reportedTrailExtent=4.0,
            repeat="partial-exposure",
        ))
        self.assertEqual(clipped["decision"], "rejected")
        self.assertIn(_MODULE.TRAIL_TOKEN, clipped["rejectedClaims"])

    def test_display_average_is_rejected(self):
        result = evaluate(payload(domain="display"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unnormalized_weights_are_not_renormalized(self):
        result = evaluate(payload(
            weights=[1.0, 1.0],
            linearValues=[1.0, 1.0],
            velocity=0.0,
            acceleration=0.0,
            reportedEnergy=2.0,
            reportedTrailExtent=0.0,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNNORMALIZED_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.ENERGY_TOKEN, result["rejectedClaims"])
        self.assertIn("linearEnergy=2", result["preservedResults"])

    def test_inpaint_is_rejected_even_when_energy_matches(self):
        result = evaluate(payload(geometry=geometry(inpaint=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("inpaint", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
