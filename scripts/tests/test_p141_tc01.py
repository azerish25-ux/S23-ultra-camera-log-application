"""Tests for TC-P141-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc01",
        "repeat": "lens",
        "assets": _GATE.fixture_assets(),
        "field": "lens",
        "factKnown": False,
        "factValue": None,
        "markedDocumented": False,
        "reconstructionLabel": "creative-reconstruction",
    }
    base.update(overrides)
    return base


class TCP14101(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unknown_fact_allows_a_labelled_reconstruction(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertFalse(record["factKnown"])
        self.assertIsNone(record["factValue"])
        self.assertEqual(record["reconstructionLabel"], "creative-reconstruction")
        self.assertEqual(result["preservedResults"][1]["excludedAssetIds"], [_GATE.STILL_ID])
        self.assertEqual(_MODULE.CASE["name"], "Missing production fact")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "plausible-equipment-guess-marked-documented")

    def test_documented_guess_is_rejected_and_the_fact_stays_unknown(self):
        result = evaluate(payload(factValue="Cooke S4", markedDocumented=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIsNone(result["preservedResults"][2]["factValue"])
        self.assertIn("p141-tc01", result["preservedResults"])

    def test_unlabelled_reconstruction_is_rejected(self):
        result = evaluate(payload(reconstructionLabel="probably-a-cooke"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLABELLED, result["rejectedClaims"])

    def test_known_fact_is_recorded(self):
        result = evaluate(
            payload(factKnown=True, factValue="Cooke S4", markedDocumented=True, reconstructionLabel=None)
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["factValue"], "Cooke S4")

    def test_unlicensed_redistribution_is_rejected_with_the_fact(self):
        assets = [_GATE.production_still(redistribute=True)]
        result = evaluate(payload(assets=assets, field="stock", repeat="stock"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.REDISTRIBUTE_WITHOUT_LICENCE, result["rejectedClaims"])
        self.assertIsNone(result["preservedResults"][2]["factValue"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc01-process"
        result = evaluate(payload(evidenceId=evidence, repeat="process", field="process"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(field="aperture"))
        with self.assertRaises(ValueError):
            evaluate(payload(factKnown=True, factValue=None))
