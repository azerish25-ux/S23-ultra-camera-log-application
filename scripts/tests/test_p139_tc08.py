"""Tests for TC-P139-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def recipes():
    return [
        {
            "id": "popular-creative",
            "rating": 4.8,
            "evidence": "creative",
            "stock": None,
            "lens": None,
        },
        {
            "id": "sourced",
            "rating": 3.1,
            "evidence": "documented",
            "stock": "Kodak Vision3 250D",
            "lens": None,
        },
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p139-tc08",
        "repeat": "blind-comparison",
        "recipes": recipes(),
        "chosenId": "sourced",
    }
    base.update(_MODULE._CORE.bundle_for())
    base.update(overrides)
    return base


class TCP13908(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_preference_stays_apart_from_the_historical_claim(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("preference=popular-creative", result["preservedResults"])
        self.assertIn("historicalClaim=sourced", result["preservedResults"])
        self.assertIn("appearance preference stays separate from the historical claim", result["reasons"])

    def test_popularity_cannot_certify_a_lens(self):
        chosen = recipes()
        chosen[0] = {
            "id": "popular-creative",
            "rating": 4.8,
            "evidence": "documented",
            "stock": "Kodak Vision3 250D",
            "lens": "Cooke S4",
        }
        result = evaluate(payload(recipes=chosen, chosenId="popular-creative", repeat="expert-review"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("historicalClaim=sourced", result["preservedResults"])
        self.assertIn("p139-tc08", result["preservedResults"])

    def test_conflicting_sources_are_not_settled_by_rating(self):
        conflicting = recipes()
        conflicting.append(
            {
                "id": "other-source",
                "rating": 4.9,
                "evidence": "documented",
                "stock": "Eastman Double-X",
                "lens": None,
            }
        )
        rejected = evaluate(
            payload(recipes=conflicting, chosenId="other-source", repeat="conflicting-sources")
        )
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, rejected["rejectedClaims"])
        self.assertIn("conflictingStocks=Eastman Double-X,Kodak Vision3 250D", rejected["preservedResults"])
        kept = evaluate(
            payload(
                recipes=conflicting,
                chosenId="sourced",
                repeat="conflicting-sources",
                evidenceId="p139-tc08-conflict",
            )
        )
        self.assert_contract(kept, "p139-tc08-conflict")
        self.assertEqual(kept["decision"], "recorded")
        self.assertIn("conflictingStocks=Eastman Double-X,Kodak Vision3 250D", kept["preservedResults"])
        self.assertIn("historicalClaim=sourced", kept["preservedResults"])

    def test_mutated_facts_are_rejected(self):
        result = evaluate(payload(mutated_facts=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(chosenId="missing"))
