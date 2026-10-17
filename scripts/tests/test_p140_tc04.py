"""Tests for TC-P140-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    document = _GATE.fixture_document()
    base = {
        "evidenceId": "p140-tc04",
        "repeat": "format",
        "claim": "offline-lookup",
        "catalogue": document["catalogue"],
        "query": document["query"],
        "filters": document["filters"],
        "typoTolerance": 1,
        "sort": "id",
        "remote_model": False,
        "network_used": False,
        "dropQueryTokens": False,
        "recommendationIds": [],
    }
    base.update(overrides)
    return base


class TCP14004(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_misspelled_offline_filter_returns_evidence_status(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        trace = result["preservedResults"][1]
        self.assertEqual(trace["ids"], ["night-hunter-lf"])
        self.assertEqual(trace["repeatedIds"], trace["ids"])
        self.assertEqual(trace["matches"][0]["evidenceStatus"], "partial")
        self.assertFalse(trace["remoteCall"])
        self.assertFalse(trace["networkUsed"])
        self.assertEqual(_MODULE.CASE["name"], "Offline search ambiguity")

    def test_alternate_title_and_stock_filters_are_local(self):
        alternate = evaluate(payload(query="Fleuve", typoTolerance=0, filters={}, repeat="alternate title"))
        self.assert_contract(alternate)
        self.assertEqual(alternate["preservedResults"][1]["ids"], ["river-day-lf"])
        stock = evaluate(payload(
            query="double x",
            typoTolerance=0,
            filters={"monochrome": True, "sceneFamilies": "day exterior"},
            repeat="scene family",
        ))
        self.assertEqual(stock["decision"], "recorded")
        self.assertEqual(stock["preservedResults"][1]["ids"], ["river-day-lf"])
        self.assertEqual(stock["preservedResults"][1]["queryTokens"], ["double", "x"])

    def test_remote_generation_is_rejected_and_local_ids_remain(self):
        result = evaluate(payload(remote_model=True, network_used=True, repeat="monochrome"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.REMOTE_MODEL, result["rejectedClaims"])
        self.assertIn(_GATE.NETWORK_USED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["ids"], ["night-hunter-lf"])
        self.assertFalse(result["preservedResults"][1]["remoteCall"])

    def test_empty_query_does_not_recommend(self):
        result = evaluate(payload(query="", filters={"formats": "large-format"}, recommendationIds=["river-day-lf"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.EMPTY_RECOMMENDATION, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["ids"], [])
        self.assertTrue(result["preservedResults"][1]["explicitEmpty"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sort="rating"))
