"""Tests for TC-P143-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc08",
        "repeat": "blind-comparison",
        "looks": _GATE.fixture_looks(),
        "dropAmbiguous": False,
        "appearancePreference": 4.5,
        "evidenceCompleteness": 0.25,
        "recipeStatus": "reconstructed",
        "popularityCertifies": False,
        "certifiedIdentification": None,
    }
    base.update(overrides)
    return base


class TCP14308(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_preference_stays_separate_from_evidence(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["appearancePreference"], 4.5)
        self.assertEqual(record["evidenceCompleteness"], 0.25)
        self.assertNotEqual(record["appearancePreference"], record["evidenceCompleteness"])
        self.assertEqual(record["recipeStatus"], "reconstructed")
        self.assertIsNone(record["certifiedIdentification"])
        self.assertTrue(record["preferenceSeparateFromEvidence"])
        self.assertEqual(len(result["preservedResults"][1]["acceptedKeys"]), 2)
        self.assertEqual(_MODULE.CASE["name"], "Preference mistaken for factual accuracy")

    def test_popularity_cannot_certify_an_identification(self):
        result = evaluate(payload(popularityCertifies=True, certifiedIdentification="Kodak 5219"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["evidenceCompleteness"], 0.25)
        self.assertIn("p143-tc08", result["preservedResults"])

    def test_reconstructed_identification_is_rejected(self):
        result = evaluate(payload(certifiedIdentification="Cooke S4"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_sourced_identification_is_recorded(self):
        result = evaluate(payload(
            recipeStatus="sourced",
            evidenceCompleteness=0.9,
            certifiedIdentification="Kodak 5219",
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["certifiedIdentification"], "Kodak 5219")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc08-expert"
        result = evaluate(payload(evidenceId=evidence, repeat="expert-review"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(recipeStatus="popular"))
