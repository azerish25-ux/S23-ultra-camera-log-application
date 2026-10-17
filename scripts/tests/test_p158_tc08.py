"""Tests for TC-P158-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15808(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("sensor-derived Log was not established", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failures_and_setup_stay_in_the_archive(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["failuresKnown"], 2)
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_promotional_reel_is_rejected(self):
        result = evaluate(payload(
            promotionalReelOnly=True,
            favorableOnly=True,
            failedExperimentIds=[],
            failuresKnown=2,
            setupDetails=[],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.OMITTED_FAILURES, result["rejectedClaims"])
        self.assertIn(_MODULE.SETUP_OMITTED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitted_failures_are_rejected(self):
        result = evaluate(payload(failedExperimentIds=["ghost-fail"], failuresKnown=2))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OMITTED_FAILURES, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_merge_without_separate_measurements_is_rejected(self):
        result = evaluate(payload(retainedHighlights={"measured": False, "value": 0}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.MOTION_AND_HIGHLIGHTS_NOT_SEPARATE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc08-optics"
        result = evaluate(payload(evidenceId=evidence, repeat="optics"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(failuresKnown=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(failedExperimentIds=["a", "b", "c"], failuresKnown=2))
