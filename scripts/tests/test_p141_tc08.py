"""Tests for TC-P141-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc08",
        "repeat": "blind comparisons",
        "assets": _GATE.fixture_assets(),
        "popularity": 0.95,
        "evidenceCompleteness": 0.3,
        "certifiesStock": False,
        "certifiesLens": False,
        "stockEvidence": False,
        "lensEvidence": True,
    }
    base.update(overrides)
    return base


class TCP14108(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_popularity_stays_separate_from_evidence(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["popularity"], 0.95)
        self.assertEqual(record["evidenceCompleteness"], 0.3)
        self.assertFalse(record["certifiesStock"])
        self.assertFalse(record["certifiesLens"])
        self.assertTrue(record["preferenceSeparate"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "popularity-certifies-stock-or-lens")

    def test_popularity_cannot_certify_stock_or_lens(self):
        stock = evaluate(payload(certifiesStock=True))
        self.assert_contract(stock)
        self.assertEqual(stock["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, stock["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], stock["reasons"])
        self.assertFalse(stock["preservedResults"][2]["certifiesStock"])
        lens = evaluate(payload(certifiesLens=True, lensEvidence=False, repeat="expert review"))
        self.assertEqual(lens["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, lens["rejectedClaims"])

    def test_evidence_may_support_an_identification(self):
        result = evaluate(payload(certifiesStock=True, stockEvidence=True, repeat="conflicting production sources"))
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["certifiesStock"])
        self.assertEqual(result["preservedResults"][2]["popularity"], 0.95)

    def test_unlicensed_asset_is_still_rejected(self):
        result = evaluate(payload(assets=[_GATE.production_still(licence="public web page")]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PUBLIC_WEB_NOT_LICENCE, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][2]["certifiesStock"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc08-review"
        result = evaluate(payload(evidenceId=evidence, repeat="expert review"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(popularity=1.4))
        with self.assertRaises(ValueError):
            evaluate(payload(evidenceCompleteness=float("nan")))
        with self.assertRaises(ValueError):
            evaluate(payload(certifiesLens="yes"))
