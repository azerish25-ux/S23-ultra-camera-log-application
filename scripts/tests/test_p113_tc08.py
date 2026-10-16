"""Tests for TC-P113-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p113_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p113_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
EFFECTS = (
    "stabilization",
    "virtual-focus",
    "motion-integration",
    "film-finishing",
)


def payload(**overrides):
    base = {
        "evidenceId": "p113-evidence",
        "repeat": "scene-cut",
        "effects": list(EFFECTS),
        "combinedEvaluated": True,
        "individualResultsOnly": False,
        "sharedGeometryId": "geom-1",
        "geometryIds": {name: "geom-1" for name in EFFECTS},
        "cadenceBefore": 24,
        "cadenceAfter": 24,
        "doubledEdges": False,
        "unstableMasks": False,
        "motionConfidence": 0.8,
        "lowConfidenceQualified": False,
        "sceneCut": True,
        "historyCrossesCut": False,
        "chunkResume": False,
        "stateRestored": True,
        "shutterAngleDegrees": 180,
        "fps": 24,
        "sensorConfirmed": False,
        "measurementId": None,
        "syntheticIntegration": False,
    }
    base.update(overrides)
    return base


class TCP11308(unittest.TestCase):
    def assert_contract(self, result, evidence="p113-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P113-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_combined_regression_preserves_geometry_and_cadence(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("shared-geometry:geom-1", result["preservedResults"])
        self.assertIn("effective-exposure-seconds:1/48", result["preservedResults"])
        self.assertIn("source-cadence-fps:24", result["preservedResults"])
        resume = evaluate(payload(repeat="chunk-resume", chunkResume=True, stateRestored=True, sceneCut=False))
        self.assertEqual(resume["decision"], "recorded")
        low = evaluate(payload(
            repeat="low-confidence-motion",
            sceneCut=False,
            motionConfidence=0.2,
            lowConfidenceQualified=True,
        ))
        self.assertEqual(low["decision"], "recorded")

    def test_independent_success_cannot_replace_the_combined_regression(self):
        result = evaluate(payload(individualResultsOnly=True, combinedEvaluated=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-success-cannot-replace-combined", result["rejectedClaims"])

    def test_cadence_edges_and_masks_fail_the_combined_check(self):
        cadence = evaluate(payload(cadenceAfter=30))
        self.assertEqual(cadence["decision"], "rejected")
        self.assertIn("unexplained-cadence-change", cadence["rejectedClaims"])
        edges = evaluate(payload(doubledEdges=True))
        self.assertEqual(edges["decision"], "rejected")
        self.assertIn("doubled-edges", edges["rejectedClaims"])
        masks = evaluate(payload(unstableMasks=True))
        self.assertEqual(masks["decision"], "rejected")
        self.assertIn("unstable-masks", masks["rejectedClaims"])
        cut = evaluate(payload(historyCrossesCut=True))
        self.assertEqual(cut["decision"], "rejected")
        self.assertIn("scene-cut-history-leak", cut["rejectedClaims"])
        unqualified = evaluate(payload(
            repeat="low-confidence-motion",
            motionConfidence=0.2,
            lowConfidenceQualified=False,
        ))
        self.assertEqual(unqualified["decision"], "rejected")
        self.assertIn("low-confidence-motion-unqualified", unqualified["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(shutterAngleDegrees=0))
        with self.assertRaises(ValueError):
            evaluate(payload(fps=-4))
        with self.assertRaises(ValueError):
            evaluate(payload(effects=["stabilization"]))
