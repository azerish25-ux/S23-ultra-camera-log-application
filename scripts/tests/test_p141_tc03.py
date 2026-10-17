"""Tests for TC-P141-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def historical():
    return {"lens": "Cooke S4", "stock": "5207", "process": "bleach-bypass"}


def derivative(**overrides):
    value = {
        "version_id": "reconstruction-2",
        "virtual_aperture": "T2.8",
        "grade": "print-light",
        "grain": "fine",
        "lens": "Cooke S4",
        "stock": "5207",
        "process": "bleach-bypass",
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc03",
        "repeat": "recipe save",
        "assets": _GATE.fixture_assets(),
        "historical": historical(),
        "derivative": derivative(),
    }
    base.update(overrides)
    return base


class TCP14103(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_new_version_keeps_historical_facts(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["historical"], historical())
        self.assertEqual(record["version_id"], "reconstruction-2")
        self.assertEqual(record["replacedFacts"], [])
        self.assertEqual(_MODULE.CASE["negative"], "User preferences must not replace the cinematographer\u2019s sourced metadata.")

    def test_user_preference_replacing_stock_is_rejected(self):
        result = evaluate(payload(derivative=derivative(stock="user-favourite")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["historical"]["stock"], "5207")
        self.assertEqual(result["preservedResults"][2]["replacedFacts"], ["stock"])

    def test_reusing_the_historical_version_id_is_rejected(self):
        result = evaluate(payload(derivative=derivative(version_id="historical"), repeat="rename"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SAME_VERSION, result["rejectedClaims"])

    def test_unlicensed_redistribution_is_rejected(self):
        result = evaluate(payload(assets=[_GATE.production_still(redistribute=True)], repeat="share"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PUBLIC_URL_NULL_LICENCE, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["historical"]["lens"], "Cooke S4")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc03-update"
        result = evaluate(payload(evidenceId=evidence, repeat="update from a newer catalogue package"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(derivative=derivative(virtual_aperture="")))
        with self.assertRaises(ValueError):
            evaluate(payload(historical={"lens": "Cooke S4"}))
