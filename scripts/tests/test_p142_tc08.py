"""Tests for TC-P142-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    recipes = overrides.pop("recipes", _MODULE.clean_recipes())
    base = {
        "evidenceId": "p142-tc08",
        "repeat": "blind-comparison",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "recipes": recipes,
        "evidenceRanking": _MODULE.evidence_order(recipes),
        "preferenceRanking": _MODULE.preference_order(recipes),
    }
    base.update(overrides)
    return base


class TCP14208(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_preference_stays_apart_from_evidence(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        kept = result["preservedResults"][2]
        self.assertEqual(kept["evidenceRanking"], ["sourced", "popular"])
        self.assertEqual(kept["preferenceRanking"], ["popular", "sourced"])
        self.assertTrue(kept["ratingsSeparateFromEvidence"])
        self.assertEqual(result["preservedResults"][1]["role"], "parameter-suggestion")

    def test_popularity_cannot_certify_stock_or_lens(self):
        recipes = _MODULE.clean_recipes()
        recipes[0]["certifiesStock"] = True
        recipes[0]["certifiesLens"] = True
        result = evaluate(payload(recipes=recipes))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_historical_claim_without_evidence_is_rejected(self):
        recipes = _MODULE.clean_recipes()
        recipes[0]["historicalClaim"] = True
        result = evaluate(payload(recipes=recipes, repeat="expert-review"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_rating_order_used_as_evidence_is_rejected(self):
        recipes = _MODULE.clean_recipes()
        result = evaluate(payload(
            recipes=recipes,
            evidenceRanking=_MODULE.preference_order(recipes),
            preferenceRanking=_MODULE.preference_order(recipes),
            repeat="conflicting-sources",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PREFERENCE_AS_EVIDENCE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p142-tc08-expert"
        result = evaluate(payload(evidenceId=evidence, repeat="expert-review"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(recipes=_MODULE.clean_recipes()[:1]))
