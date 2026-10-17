"""Tests for TC-P138-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def ratings(**overrides):
    value = {
        "daylight-5219": 1,
        "low-light-5219": 2,
        "monochrome-5222": 1.5,
        "format-5207": 1,
        "scene-12": 9,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc08",
        "repeat": "blind comparisons",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "ratings": ratings(),
        "claimedFactualRecipeId": None,
    }
    base.update(overrides)
    return base


class TCP13808(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_higher_rating_does_not_certify_the_reconstruction(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][2]
        self.assertEqual(detail["highestRatedRecipeId"], "scene-12")
        self.assertEqual(detail["highestRating"], 9.0)
        self.assertIn("daylight-5219", detail["sourcedRecipeIds"])
        self.assertNotIn("scene-12", detail["sourcedRecipeIds"])
        self.assertTrue(detail["preferenceSeparateFromEvidence"])
        self.assertIsNone(result["preservedResults"][1]["entries"][4]["stock"])
        self.assertEqual(_MODULE.CASE["name"], "Preference mistaken for factual accuracy")

    def test_popularity_cannot_certify_stock_or_lens(self):
        result = evaluate(payload(
            repeat="expert review",
            claimedFactualRecipeId="scene-12",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertFalse(result["preservedResults"][2]["preferenceSeparateFromEvidence"])
        self.assertEqual(result["preservedResults"][1]["entries"][1]["lens"], "Cooke S4 35mm")

    def test_sourced_claim_is_recorded_even_when_it_is_not_popular(self):
        evidence = "p138-tc08-sources"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="conflicting production sources",
            claimedFactualRecipeId="low-light-5219",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["claimedFactualRecipeId"], "low-light-5219")
        self.assertNotEqual(
            result["preservedResults"][2]["claimedFactualRecipeId"],
            result["preservedResults"][2]["highestRatedRecipeId"],
        )

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(claimedFactualRecipeId="missing"))
        incomplete = ratings()
        del incomplete["scene-12"]
        with self.assertRaises(ValueError):
            evaluate(payload(ratings=incomplete))
        with self.assertRaises(ValueError):
            evaluate(payload(ratings=ratings(**{"scene-12": True})))
