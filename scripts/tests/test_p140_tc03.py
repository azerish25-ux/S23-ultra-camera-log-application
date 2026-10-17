"""Tests for TC-P140-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def facts(**overrides):
    base = {
        "aperture": "T2.0",
        "grade": "print contrast neutral",
        "grain": "fine",
        "stock": "Eastman Double-X",
        "lens": "50mm",
    }
    base.update(overrides)
    return base


def payload(**overrides):
    base = {
        "evidenceId": "p140-tc03",
        "repeat": "save",
        "historicalId": "night-hunter-facts",
        "title": "Night Hunter",
        "originalFacts": facts(),
        "historicalAfter": facts(),
        "derivative": {
            "id": "user-night-grade",
            "name": "Night Hunter user grade",
            "virtualAperture": "T4.0",
            "grade": "crushed blacks",
            "grain": "heavy",
            "provenance": "user derivative",
        },
        "localOnly": True,
    }
    base.update(overrides)
    return base


class TCP14003(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_derivative_keeps_historical_facts_private(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["changedFields"], [])
        self.assertEqual(kept["originalFacts"]["aperture"], "T2.0")
        self.assertEqual(kept["publicIds"], ["night-hunter-facts"])
        self.assertEqual(kept["privateExcluded"], "user-night-grade")
        self.assertNotIn("user-night-grade", kept["publicIds"])
        self.assertIn("cinematographer\u2019s", _MODULE.CASE["negative"])

    def test_overwriting_sourced_grade_is_rejected(self):
        result = evaluate(payload(historicalAfter=facts(grade="crushed blacks"), repeat="update"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["originalFacts"]["grade"], "print contrast neutral")
        self.assertEqual(result["preservedResults"][1]["changedFields"], ["grade"])

    def test_publishing_the_user_recipe_is_rejected(self):
        result = evaluate(payload(localOnly=False, repeat="share"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLISHED, result["rejectedClaims"])
        self.assertIn("user-night-grade", result["preservedResults"][1]["publicIds"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p140-tc03-rename"
        result = evaluate(payload(evidenceId=evidence, repeat="rename"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        derivative = payload()["derivative"]
        derivative["id"] = "night-hunter-facts"
        with self.assertRaises(ValueError):
            evaluate(payload(derivative={**derivative, "provenance": "  "}))
        result = evaluate(payload(derivative=derivative))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REUSED_ID, result["rejectedClaims"])
