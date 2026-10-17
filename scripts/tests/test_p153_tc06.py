"""Tests for TC-P153-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15306(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_single_exposure_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["computational"])
        self.assertEqual(_MODULE.CASE["name"], "Computational capture overclaim")

    def test_labeled_measured_merge_is_recorded(self):
        result = evaluate(payload(
            exposure_count=3,
            presented_as="computational-merge",
            motion_artifacts_measured=True,
            retained_information_measured=True,
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][3]["computational"])

    def test_merge_presented_as_one_exposure_is_rejected(self):
        result = evaluate(payload(
            exposure_count=3,
            presented_as="single-unchanged-sensor-exposure",
            motion_artifacts_measured=False,
            retained_information_measured=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MERGE_PROVENANCE, result["rejectedClaims"])
        self.assertIn(_MODULE.LABEL, result["rejectedClaims"])
        self.assertIn(_MODULE.UNMEASURED_MERGE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc06-ghosts"
        result = evaluate(payload(evidenceId=evidence, repeat="temporal-ghosts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(exposure_count=0))
