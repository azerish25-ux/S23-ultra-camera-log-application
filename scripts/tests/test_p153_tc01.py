"""Tests for TC-P153-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15301(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_isolated_storage_limit_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["presented_cause"], "storage")
        self.assertTrue(result["preservedResults"][3]["isolated"])
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.SLOW_PATH_VENDOR, "slow-path-assumed-vendor-blocking")
        self.assertIn(_MODULE.CASE["repeat"], result["openQuestions"])

    def test_storage_presented_as_firmware_is_rejected(self):
        result = evaluate(payload(presented_cause="scheduling", isolated=False, proposed_modification="firmware"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SLOW_PATH_VENDOR, result["rejectedClaims"])
        self.assertIn(_MODULE.ISOLATION_REQUIRED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_unmeasured_firmware_hypothesis_is_rejected_inside_the_case(self):
        result = evaluate(payload(hypotheses=[_GATE.fixture_hypothesis(blamed="firmware", measurement_id=None)]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNMEASURED_FIRMWARE, result["rejectedClaims"])
        self.assertIn(_MODULE.SLOW_PATH_VENDOR, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc01-saved-source"
        result = evaluate(payload(evidenceId=evidence, repeat="saved-source"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(presented_cause="myth"))
