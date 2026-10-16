"""Tests for TC-P117-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc08.py",
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
        "evidenceId": "p117-combined",
        "repeat": "chunk-resumes",
        "effects": [
            "stabilization",
            "virtualFocus",
            "motionIntegration",
            "filmFinishing",
        ],
        "independentPass": {
            "stabilization": True,
            "virtualFocus": True,
            "motionIntegration": True,
            "filmFinishing": True,
        },
        "combinedMeasured": True,
        "combinedEdgeCount": 1,
        "maskStable": True,
        "sourceCadence": 24.0,
        "outputCadence": 24.0,
        "cadenceExplained": False,
        "motionConfidence": 0.8,
        "confidenceFloor": 0.5,
        "sceneCut": False,
        "cutDeclared": False,
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11708(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-combined"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Combined temporal effects")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Independent success of each effect cannot replace the combined regression.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat scene cuts, chunk resumes, and low-confidence motion estimates.",
        )

    def test_combined_regression_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(
            "sample[0] layer=depth output=(1,0) source=(0,0) status=known inCrop=yes depth=0",
            result["preservedResults"],
        )

    def test_independent_passes_do_not_replace_the_combined_run(self):
        result = evaluate(payload(combinedMeasured=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_doubled_edges_and_unstable_masks_are_rejected(self):
        edges = evaluate(payload(combinedEdgeCount=2))
        self.assertEqual(edges["decision"], "rejected")
        self.assertIn(_MODULE.DOUBLED_TOKEN, edges["rejectedClaims"])
        masks = evaluate(payload(maskStable=False))
        self.assertEqual(masks["decision"], "rejected")
        self.assertIn(_MODULE.UNSTABLE_TOKEN, masks["rejectedClaims"])

    def test_unexplained_cadence_change_is_rejected(self):
        result = evaluate(payload(outputCadence=30.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])
        explained = evaluate(payload(outputCadence=30.0, cadenceExplained=True))
        self.assertEqual(explained["decision"], "recorded")

    def test_low_confidence_and_undeclared_cut_are_rejected(self):
        low = evaluate(payload(motionConfidence=0.1, repeat="low-confidence-motion"))
        self.assertEqual(low["decision"], "rejected")
        self.assertIn(_MODULE.LOW_CONFIDENCE_TOKEN, low["rejectedClaims"])
        cut = evaluate(payload(sceneCut=True, repeat="scene-cuts"))
        self.assertEqual(cut["decision"], "rejected")
        self.assertIn(_MODULE.CUT_TOKEN, cut["rejectedClaims"])
        declared = evaluate(payload(sceneCut=True, cutDeclared=True, repeat="scene-cuts"))
        self.assertEqual(declared["decision"], "recorded")

    def test_untransformed_mask_fails_the_combined_geometry(self):
        geo = geometry()
        geo["layers"] = {
            "rgb": {"dx": 1.0, "dy": 0.0},
            "depth": {"dx": 1.0, "dy": 0.0},
            "mask": {"dx": 0.0, "dy": 0.0},
        }
        result = evaluate(payload(geometry=geo))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("color-stabilized-masks-unchanged", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
