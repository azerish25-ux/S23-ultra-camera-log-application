"""Tests for TC-P120-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
EFFECTS = ["stabilization", "virtualFocus", "motionIntegration", "filmFinishing"]


def honest_report(**overrides):
    value = {
        "shutter_angle": 180.0,
        "fps": 24.0,
        "exposure_seconds": (180.0 / 360.0) / 24.0,
        "interpolation_fraction": 0.25,
        "estimated_disclosed": True,
        "stabilization_crop_fraction": 0.08,
        "rolling_shutter_readout": "measured",
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
    base.update(overrides)
    return base


class TCP12008(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_combined_regression_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("exposure_seconds=0.0208333333333=(shutter_angle/360)/fps", result["reasons"])

    def test_independent_success_does_not_replace_combined(self):
        result = evaluate(payload(combinedMeasured=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_shutter_only_spot_check_is_rejected(self):
        result = evaluate(payload(combinationPassed=True, report={"shutter_angle": 180.0}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("shutter-only-spot-check-claimed-combination-passed", result["rejectedClaims"])
        self.assertIn("combined-report-field-missing", result["rejectedClaims"])

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

    def test_explained_cadence_change_can_be_recorded(self):
        result = evaluate(payload(outputCadence=30.0, cadenceExplained=True, repeat="chunk resume"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-cut"
        result = evaluate(payload(evidenceId=evidence, repeat="scene cut"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
