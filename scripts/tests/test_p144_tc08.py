"""Tests for TC-P144-08."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p144-tc08",
        "repeat": "blind comparisons",
        "popular": _GATE.preferred_recipe(),
        "sourced": _GATE.sourced_recipe(),
        "popularity_certifies_identification": False,
    }
    base.update(overrides)
    return base


class TCP14408(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_higher_rating_does_not_certify_identification(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertGreater(record["popular"]["enjoyment"], record["sourced"]["enjoyment"])
        self.assertGreater(record["popular"]["star_rating"], record["sourced"]["star_rating"])
        self.assertFalse(record["popular"]["identification"]["correct"])
        self.assertTrue(record["popular"]["enjoyable_and_unidentified"])
        self.assertTrue(record["sourced"]["identification"]["correct"])
        self.assertEqual(record["sourced"]["identification"]["evidence_kind"], "source")
        self.assertTrue(record["preference_separate"])
        self.assertIn(_GATE.STAR_NOTE, result["reasons"])

    def test_popularity_flag_is_rejected(self):
        result = evaluate(payload(popularity_certifies_identification=True, repeat="expert review"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.POPULARITY, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertFalse(result["preservedResults"][1]["popular"]["identification"]["correct"])
        self.assertIn("p144-tc08", result["preservedResults"])

    def test_high_enjoyment_does_not_flip_the_popular_recipe(self):
        popular = json.loads(json.dumps(_GATE.preferred_recipe()))
        popular["enjoyment"] = 1
        popular["star_rating"] = 5
        popular["identification"]["status"] = "correct"
        popular["identification"]["evidence_kind"] = "star_rating"
        result = evaluate(payload(popular=popular, repeat="conflicting production sources"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.STAR_RATING_AS_IDENTIFICATION, result["rejectedClaims"])
        self.assertIn(_GATE.MUTANT, result["rejectedClaims"])
        self.assertIn(_GATE.HIGH_ENJOYMENT_DOES_NOT_CERTIFY, result["rejectedClaims"])
        self.assertIn(_MODULE.PREFERENCE_MERGED, result["rejectedClaims"])
        kept = result["preservedResults"][1]["popular"]
        self.assertEqual(kept["enjoyment"], 1)
        self.assertFalse(kept["identification"]["correct"])
        self.assertTrue(result["preservedResults"][1]["sourced"]["identification"]["correct"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc08-expert"
        result = evaluate(payload(evidenceId=evidence, repeat="expert review"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        popular = _GATE.preferred_recipe()
        popular["coherence"] = 2
        with self.assertRaises(ValueError):
            evaluate(payload(popular=popular))
