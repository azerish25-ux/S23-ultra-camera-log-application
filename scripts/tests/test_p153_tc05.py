"""Tests for TC-P153-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15305(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_expanded_menu_without_samples_fails_the_hypothesis(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["acquisitionFailed"])
        self.assertEqual(result["preservedResults"][3]["sensor_samples"], 0)
        self.assertFalse(result["preservedResults"][3]["acquisition_claimed"])
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_visible_setting_is_not_useful_capture(self):
        result = evaluate(payload(acquisition_claimed=True, sensor_samples=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.VISIBLE_NOT_CAPTURE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p153-blocked-capability", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc05-cadence"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained-cadence"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sensor_samples=-1))
