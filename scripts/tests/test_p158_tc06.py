"""Tests for TC-P158-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15806(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_labelled_merge_keeps_provenance(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["measurementsSeparate"])
        self.assertEqual(result["preservedResults"][1]["presentedAs"], "computational-merge")
        self.assertEqual(_MODULE.CASE["name"], "Computational capture overclaim")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))

    def test_attractive_merge_cannot_erase_provenance(self):
        result = evaluate(payload(
            provenanceRetained=False,
            attractiveMerge=True,
            computationalLabel="single-sensor-exposure",
            presentedAs="single-unmodified-sensor-exposure",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.COMPUTATIONAL_LABEL_MISSING, result["rejectedClaims"])
        self.assertIn(_GATE.PRESENTED_AS_UNMODIFIED_SENSOR, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_missing_computational_label_is_rejected(self):
        result = evaluate(payload(computationalLabel="sensor-exposure"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.COMPUTATIONAL_LABEL_MISSING, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_apply_mutant_is_rejected_inside_the_case(self):
        result = evaluate(payload(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.MERGED_DR_WITHOUT_MOTION, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["motionAlignmentPresent"])
        self.assertIn("mutant rejected: " + _GATE.MUTANT, result["reasons"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc06-ghosts"
        result = evaluate(payload(evidenceId=evidence, repeat="temporal-ghosts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(provenanceRetained="yes"))
        with self.assertRaises(ValueError):
            evaluate(payload(computationalLabel=""))
