"""Tests for TC-P138-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def derivative(**overrides):
    value = {
        "recipe_id": "user-grade-2",
        "virtualAperture": None,
        "grade": "contrast-up",
        "grain": "fine",
        "stock": None,
        "lens": None,
        "traces": [],
        "replacesHistorical": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc03",
        "repeat": "save",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "derivative": derivative(),
    }
    base.update(overrides)
    return base


class TCP13803(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_new_grade_keeps_historical_stock_and_lens(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        facts = result["preservedResults"][2]["historicalFacts"]
        daylight = next(item for item in facts if item["recipe_id"] == "daylight-5219")
        self.assertEqual(daylight["stock"], "5219")
        self.assertIsNone(daylight["lens"])
        low = next(item for item in facts if item["recipe_id"] == "low-light-5219")
        self.assertEqual(low["lens"], "Cooke S4 35mm")
        self.assertEqual(result["preservedResults"][2]["derivativeRecipeId"], "user-grade-2")
        self.assertEqual(_MODULE.CASE["name"], "Creative edit overwrites evidence")

    def test_user_stock_is_rejected_and_historical_facts_remain(self):
        result = evaluate(payload(
            repeat="update",
            derivative=derivative(stock="preferred-print", replacesHistorical=True, grade="push"),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.UNSOURCED_STOCK, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        historical = result["preservedResults"][1]["entries"]
        self.assertEqual(historical[0]["stock"], "5219")
        self.assertNotEqual(historical[0]["stock"], "preferred-print")

    def test_rename_repeat_preserves_a_different_evidence_id(self):
        evidence = "p138-tc03-rename"
        result = evaluate(payload(evidenceId=evidence, repeat="rename", derivative=derivative(recipe_id="user-rename")))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(derivative=derivative(recipe_id="daylight-5219")))
        with self.assertRaises(ValueError):
            evaluate(payload(derivative=derivative(virtualAperture=None, grade=None, grain=None)))
