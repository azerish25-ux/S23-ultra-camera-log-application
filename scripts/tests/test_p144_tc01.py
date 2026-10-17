"""Tests for TC-P144-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p144-tc01",
        "repeat": "lens",
        "field": "lens",
        "fact_known": False,
        "labelled_creative_reconstruction": True,
        "marked_documented": False,
        "recipe": _GATE.preferred_recipe(),
    }
    base.update(overrides)
    return base


class TCP14401(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unknown_fact_stays_a_labelled_reconstruction(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["field"], "lens")
        self.assertFalse(record["known"])
        self.assertTrue(record["labelled_creative_reconstruction"])
        self.assertFalse(record["report"]["identification"]["correct"])
        self.assertTrue(record["report"]["enjoyable_and_unidentified"])
        self.assertEqual(_MODULE.CASE["name"], "Missing production fact")
        self.assertEqual(_MODULE.CASE["negative"], "A plausible equipment guess marked documented must fail.")

    def test_guess_marked_documented_is_rejected(self):
        result = evaluate(payload(marked_documented=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GUESS_DOCUMENTED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertFalse(result["preservedResults"][1]["report"]["identification"]["correct"])

    def test_unknown_fact_identified_from_a_source_is_rejected(self):
        result = evaluate(payload(field="stock", recipe=_GATE.sourced_recipe()))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_IDENTIFIED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc01-camera"
        result = evaluate(payload(evidenceId=evidence, repeat="camera", field="camera"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(field="director"))
