"""Tests for TC-P140-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p140-tc08",
        "repeat": "blind comparisons",
        "recipes": [
            {
                "id": "a-popular",
                "stock": "invented stock",
                "lens": "invented lens",
                "evidenceCompleteness": "preference",
                "popularity": 100,
                "preferenceRating": 5,
            },
            {
                "id": "z-sourced",
                "stock": "Eastman Double-X",
                "lens": "50mm",
                "evidenceCompleteness": "documented",
                "popularity": 1,
                "preferenceRating": 2,
            },
        ],
        "sort": "evidenceCompleteness",
        "query": "recipe",
        "popularityCertifiesStock": False,
        "popularityCertifiesLens": False,
    }
    base.update(overrides)
    return base


class TCP14008(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_documented_recipe_outranks_a_popular_preference(self):
        result = evaluate(payload(query="Double-X"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["ids"], ["z-sourced"])
        self.assertEqual(kept["orderedBy"], "evidenceCompleteness")
        self.assertFalse(kept["popularityCertifies"])
        self.assertEqual(kept["popularityOrder"][0], "a-popular")

    def test_shared_query_sorts_by_evidence_not_rating(self):
        recipes = payload()["recipes"]
        recipes[0]["stock"] = "Eastman Double-X"
        recipes[0]["lens"] = "50mm"
        result = evaluate(payload(recipes=recipes, query="50mm"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["ids"], ["z-sourced", "a-popular"])

    def test_popularity_cannot_certify_stock_or_lens(self):
        result = evaluate(payload(
            sort="popularity",
            popularityCertifiesStock=True,
            popularityCertifiesLens=True,
            repeat="expert review",
            query="50mm",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.POPULARITY_SORT, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["ids"], ["z-sourced"])
        self.assertNotEqual(result["preservedResults"][1]["ids"], ["a-popular"])
        self.assertFalse(result["preservedResults"][1]["popularityCertifies"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p140-tc08-sources"
        result = evaluate(payload(evidenceId=evidence, repeat="conflicting production sources", query="Double-X"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sort="rating"))
