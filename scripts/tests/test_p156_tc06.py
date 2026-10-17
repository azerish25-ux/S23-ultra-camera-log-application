"""Tests for TC-P156-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="moving subjects")
    base.update({
        "exposures": 3,
        "labeledComputational": True,
        "presentedAsSingleSensorExposure": False,
        "motionArtifactsMeasured": True,
        "retainedInformationMeasured": True,
    })
    base.update(overrides)
    return base


class TCP15606(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_labeled_merge_with_separate_measurements_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["merged"])
        self.assertTrue(result["preservedResults"][3]["labeledComputational"])
        self.assertEqual(_MODULE.CASE["name"], "Computational capture overclaim")

    def test_presenting_a_merge_as_one_sensor_exposure_is_rejected(self):
        result = evaluate(payload(presentedAsSingleSensorExposure=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.NOT_LABELED, result["rejectedClaims"])

    def test_unlabeled_merge_is_rejected(self):
        result = evaluate(payload(labeledComputational=False, motionArtifactsMeasured=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NOT_LABELED, result["rejectedClaims"])
        self.assertIn(_MODULE.NOT_MEASURED, result["rejectedClaims"])

    def test_a_single_exposure_is_not_a_merge(self):
        result = evaluate(payload(
            exposures=1,
            labeledComputational=False,
            motionArtifactsMeasured=False,
            retainedInformationMeasured=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][3]["merged"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc06-ghosts"
        result = evaluate(payload(evidenceId=evidence, repeat="temporal ghosts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(exposures=0))
        with self.assertRaises(ValueError):
            evaluate(payload(labeledComputational="yes"))
