"""Tests for TC-P155-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def acquisition(**overrides):
    value = {
        "exposureCount": 3,
        "label": "computational",
        "motionArtifacts": "measured",
        "retainedInformation": "measured",
        "provenance": "retained",
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="moving subjects")
    base.update({"acquisition": acquisition()})
    base.update(overrides)
    return base


class TCP15506(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_labelled_merge_with_separate_measurements_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        preserved = result["preservedResults"][3]
        self.assertEqual(preserved["label"], "computational")
        self.assertEqual(preserved["motionArtifacts"], "measured")
        self.assertEqual(preserved["retainedInformation"], "measured")
        self.assertEqual(preserved["provenance"], "retained")
        self.assertEqual(_MODULE.CASE["name"], "Computational capture overclaim")

    def test_merge_presented_as_a_single_exposure_is_rejected(self):
        result = evaluate(payload(acquisition=acquisition(
            label="single-unchanged-sensor-exposure",
            provenance="erased",
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.UNLABELLED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitted_motion_measurement_is_rejected(self):
        result = evaluate(payload(acquisition=acquisition(motionArtifacts="omitted")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MOTION_NOT_MEASURED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc06-ghosts"
        result = evaluate(payload(evidenceId=evidence, repeat="temporal ghosts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(acquisition=acquisition(exposureCount=0)))
        with self.assertRaises(ValueError):
            evaluate(payload(acquisition=acquisition(provenance="qualified")))
