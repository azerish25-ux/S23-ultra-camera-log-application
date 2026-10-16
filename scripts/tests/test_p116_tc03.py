"""Tests for TC-P116-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p116_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p116_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def timeline(**overrides):
    value = {
        "captured": [
            {"time": 0.0, "value": 0.0, "origin": "captured"},
            {"time": 1.0, "value": 2.0, "origin": "captured"},
        ],
        "estimated": [{"time": 0.5, "value": 1.0, "origin": "estimated"}],
        "withheldMidpoint": {"time": 0.5, "value": 1.0},
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p116-evidence",
        "repeat": "Repeat",
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
    base.update(timeline())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP11603(unittest.TestCase):
    def assert_contract(self, result, evidence="p116-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P116-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("interpolationFraction=1/3=0.3333333333333333", blob(result))

    def test_linear_energy_and_trail_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("integratedEnergy=2", result["reasons"])
        self.assertIn("trailExtent=2.25", result["reasons"])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

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

    def test_trail_mismatch_is_rejected(self):
        result = evaluate(payload(reportedTrailExtent=1.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ENERGY_TOKEN, result["rejectedClaims"])

    def test_partial_boundary_keeps_normalized_energy(self):
        result = evaluate(payload(partialBoundary=True, repeat="partial exposure"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("partial boundary" in item for item in result["reasons"]))

    def test_hidden_hallucination_is_rejected(self):
        result = evaluate(payload(**timeline(
            estimated=[{"time": 0.5, "value": 1.0, "origin": "captured"}],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-hallucination", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p116-accel"
        result = evaluate(payload(evidenceId=evidence, repeat="acceleration"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
