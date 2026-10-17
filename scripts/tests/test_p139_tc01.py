"""Tests for TC-P139-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    facts = _MODULE._CORE.sample_facts()
    facts["lens"] = None
    base = {
        "evidenceId": "p139-tc01",
        "repeat": "lens",
        "removedField": "lens",
        "guess": None,
    }
    base.update(_MODULE._CORE.bundle_for(facts))
    base.update(overrides)
    return base


class TCP13901(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_unknown_lens_allows_a_labelled_reconstruction(self):
        body = payload()
        result = evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("unknown=lens", result["preservedResults"])
        self.assertIsNone(body["productionFacts"]["lens"])
        self.assertIn("label=creative-reconstruction", result["preservedResults"])
        self.assertIn("label=user-reconstruction", result["preservedResults"])

    def test_documented_guess_is_rejected_and_evidence_remains(self):
        result = evaluate(
            payload(
                guess={"field": "lens", "value": "Cooke S4", "marked": "documented"},
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("guess=lens:documented", result["preservedResults"])

    def test_creative_label_for_the_same_guess_is_recorded(self):
        result = evaluate(
            payload(guess={"field": "lens", "value": "Cooke S4", "marked": "creative-reconstruction"})
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_each_removed_fact_stays_unknown(self):
        for repeat, field in _MODULE.FIELD_BY_REPEAT.items():
            facts = _MODULE._CORE.sample_facts()
            facts[field] = None
            body = _MODULE._CORE.bundle_for(facts)
            result = evaluate(payload(repeat=repeat, removedField=field, **body))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded", repeat)
            self.assertIsNone(body["productionFacts"][field])

    def test_mutated_facts_are_rejected(self):
        result = evaluate(payload(mutated_facts=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        facts = _MODULE._CORE.sample_facts()
        facts["stock"] = None
        evidence = "p139-tc01-stock"
        result = evaluate(payload(evidenceId=evidence, repeat="stock", removedField="stock", **_MODULE._CORE.bundle_for(facts)))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(removedField="not-a-fact"))
