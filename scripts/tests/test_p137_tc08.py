"""Tests for TC-P137-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def recipe(ident, rating, stock, lens, certified=False):
    return {
        "id": ident,
        "rating": rating,
        "stock": stock,
        "lens": lens,
        "certifiedByRating": certified,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p137-tc08",
        "repeat": "blind comparisons",
        "recipes": [
            recipe(
                "popular",
                4.8,
                _GATE.make_field("stock", "reconstruction", "print-grain"),
                _GATE.make_field("lens", "reconstruction", "virtual-spherical-50mm"),
            ),
            recipe(
                "sourced",
                3.1,
                _GATE.make_field("stock", "fact", "Eastman 5293", "src-northwater-stock"),
                _GATE.make_field("lens", "unknown", None, None),
            ),
        ],
    }
    base.update(overrides)
    return base


def field_named(recipe_row, name):
    return next(field for field in recipe_row["fields"] if field["name"] == name)


class TCP13708(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_higher_rating_does_not_promote_reconstruction(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertTrue(detail["preferenceSeparate"])
        self.assertEqual(detail["preferences"][0], {"id": "popular", "rating": 4.8})
        popular = next(item for item in detail["recipes"] if item["id"] == "popular")
        sourced = next(item for item in detail["recipes"] if item["id"] == "sourced")
        self.assertEqual(field_named(popular, "stock")["state"], "reconstruction")
        self.assertEqual(field_named(popular, "lens")["state"], "reconstruction")
        self.assertEqual(field_named(sourced, "stock")["state"], "fact")
        self.assertEqual(field_named(sourced, "stock")["source_id"], "src-northwater-stock")
        self.assertEqual(field_named(sourced, "lens")["state"], "unknown")
        self.assertIsNone(field_named(sourced, "lens")["value"])
        self.assertGreater(detail["stateCounts"]["fact"], 0)
        self.assertGreater(detail["stateCounts"]["reconstruction"], 0)
        self.assertGreater(detail["stateCounts"]["unknown"], 0)
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Preference mistaken for factual accuracy")

    def test_popularity_cannot_certify_stock_or_lens(self):
        recipes = [
            recipe(
                "popular",
                4.9,
                _GATE.make_field("stock", "fact", "Eastman 5293", "popularity"),
                _GATE.make_field("lens", "fact", _GATE.GUESSED_LENS, "rating"),
                certified=True,
            ),
            recipe(
                "sourced",
                3.0,
                _GATE.make_field("stock", "fact", "Eastman 5293", "src-northwater-stock"),
                _GATE.make_field("lens", "unknown", None, None),
            ),
        ]
        result = evaluate(payload(recipes=recipes, repeat="expert review"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.POPULARITY_CERTIFIES, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        detail = result["preservedResults"][1]
        popular = next(item for item in detail["recipes"] if item["id"] == "popular")
        sourced = next(item for item in detail["recipes"] if item["id"] == "sourced")
        self.assertEqual(field_named(popular, "stock")["state"], "reconstruction")
        self.assertIsNone(field_named(popular, "stock")["source_id"])
        self.assertEqual(field_named(popular, "lens")["state"], "unknown")
        self.assertIsNone(field_named(popular, "lens")["value"])
        self.assertEqual(field_named(sourced, "stock")["state"], "fact")
        self.assertEqual(field_named(sourced, "stock")["value"], "Eastman 5293")
        self.assertEqual(detail["preferences"][0]["rating"], 4.9)

    def test_repeat_comparisons_keep_preference_separate(self):
        for repeat in ("blind comparisons", "expert review", "conflicting production sources"):
            result = evaluate(payload(repeat=repeat))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded", repeat)
            self.assertTrue(result["preservedResults"][1]["preferenceSeparate"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(recipes=[]))
