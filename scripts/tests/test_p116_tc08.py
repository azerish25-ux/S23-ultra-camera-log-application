"""Tests for TC-P116-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p116_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p116_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
EFFECTS = ["stabilization", "virtualFocus", "motionIntegration", "filmFinishing"]


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
        "effects": list(EFFECTS),
        "independentPass": {name: True for name in EFFECTS},
        "combinedMeasured": True,
        "combinedEdgeCount": 1,
        "maskStable": True,
        "sourceCadence": 24.0,
        "outputCadence": 24.0,
        "cadenceExplained": False,
        "rgbGeometryId": "geom-a",
        "depthGeometryId": "geom-a",
    }
    base.update(timeline())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP11608(unittest.TestCase):
    def assert_contract(self, result, evidence="p116-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P116-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("interpolationFraction=1/3=0.3333333333333333", blob(result))

    def test_combined_regression_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

    def test_independent_success_does_not_replace_combined(self):
        result = evaluate(payload(combinedMeasured=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_doubled_edges_are_rejected(self):
        result = evaluate(payload(combinedEdgeCount=2))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DOUBLED_TOKEN, result["rejectedClaims"])

    def test_unstable_mask_and_cadence_and_geometry_are_rejected(self):
        result = evaluate(payload(
            maskStable=False,
            outputCadence=30.0,
            depthGeometryId="geom-b",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNSTABLE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.GEOMETRY_TOKEN, result["rejectedClaims"])

    def test_hidden_hallucination_is_rejected(self):
        result = evaluate(payload(**timeline(
            estimated=[{"time": 0.5, "value": 1.0, "origin": "captured"}],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-hallucination", result["rejectedClaims"])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p116-cut"
        result = evaluate(payload(evidenceId=evidence, repeat="scene cut"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
