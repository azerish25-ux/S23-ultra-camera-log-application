"""Tests for TC-P160-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="moving subjects")
    base.update({
        "exposureCount": 3,
        "presentedAsUnchangedSensorExposure": False,
        "labeledComputational": True,
        "motionArtifactsMeasured": True,
        "retainedInformationMeasured": True,
        "provenanceErased": False,
    })
    base.update(overrides)
    return base


class TCP16006(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-06")
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
        self.assertEqual(_MODULE.CASE["name"], "Computational capture overclaim")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "attractive-merge-erases-provenance")

    def test_erased_provenance_is_rejected(self):
        result = evaluate(payload(provenanceErased=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_unchanged_sensor_presentation_is_rejected(self):
        result = evaluate(payload(presentedAsUnchangedSensorExposure=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLABELED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_combined_artifact_measurement_is_rejected(self):
        result = evaluate(payload(motionArtifactsMeasured=False, retainedInformationMeasured=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_SEPARATED, result["rejectedClaims"])

    def test_single_exposure_is_recorded(self):
        result = evaluate(payload(
            exposureCount=1,
            labeledComputational=False,
            motionArtifactsMeasured=False,
            retainedInformationMeasured=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][3]["merged"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc06-ghosts"
        result = evaluate(payload(evidenceId=evidence, repeat="temporal ghosts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(exposureCount=0))
        with self.assertRaises(ValueError):
            evaluate(payload(exposureCount=True))
