"""Tests for TC-P153-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15308(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failures_and_setup_are_preserved(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["missingFailures"], [])
        self.assertEqual(result["preservedResults"][3]["missingSetup"], [])
        self.assertFalse(result["preservedResults"][3]["promotional_only"])
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")

    def test_omitted_failures_are_rejected(self):
        result = evaluate(payload(archived_failure_ids=["exp-codec"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FAILURES, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][3]["missingFailures"], ["exp-thermal"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_missing_setup_is_rejected(self):
        result = evaluate(payload(setup={"device": "host-fixture", "software": "p153"}))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SETUP, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][3]["missingSetup"], ["capture-settings"])

    def test_promotional_reel_is_rejected(self):
        result = evaluate(payload(promotional_only=True, outputs=[{"id": "reel", "favorable": True}]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REEL, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertTrue(result["preservedResults"][3]["favorableOnly"])
        self.assertIn("p153-blocked-capability", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc08-optics"
        result = evaluate(payload(evidenceId=evidence, repeat="optics"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(required_setup=[]))
            evaluate(payload(outputs=[{"id": "clip-a", "favorable": True}, {"id": "clip-a", "favorable": False}]))
