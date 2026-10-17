"""Tests for TC-P138-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc04",
        "repeat": "format",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "query": "North See Ledger",
        "aliases": {"daylight-5219": ["Northsea Ledger"]},
        "networkRequired": False,
    }
    base.update(overrides)
    return base


class TCP13804(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_misspelled_title_matches_locally_with_evidence_status(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        candidates = result["preservedResults"][2]["candidates"]
        self.assertGreaterEqual(len(candidates), 5)
        self.assertTrue(all(item["distance"] == 1 and item["matchedOn"] == "film_title" for item in candidates))
        statuses = {item["recipe_id"]: item["evidenceStatus"] for item in candidates}
        self.assertEqual(statuses["daylight-5219"], "sourced")
        self.assertEqual(statuses["scene-12"], "unknown")
        self.assertTrue(any("local candidates:" in reason for reason in result["reasons"]))
        self.assertIsNone(next(entry["lens"] for entry in result["preservedResults"][1]["entries"] if entry["recipe_id"] == "scene-12"))

    def test_stock_typo_and_variant_filter_are_local(self):
        stock = evaluate(payload(query="5218", repeat="stock names", aliases={}))
        self.assertEqual(stock["decision"], "recorded")
        best = stock["preservedResults"][2]["candidates"][0]
        self.assertEqual(best["recipe_id"], "daylight-5219")
        self.assertEqual(best["matchedOn"], "stock")
        self.assertEqual(best["distance"], 1)
        self.assertEqual(best["stock"], "5219")
        mono = evaluate(payload(query="monochrome", repeat="monochrome", aliases={}))
        self.assertEqual(mono["decision"], "recorded")
        self.assertEqual(
            [item["recipe_id"] for item in mono["preservedResults"][2]["candidates"]],
            ["monochrome-5222"],
        )
        self.assertEqual(mono["preservedResults"][2]["candidates"][0]["evidenceStatus"], "sourced")

    def test_remote_generation_is_rejected_but_local_candidates_remain(self):
        result = evaluate(payload(networkRequired=True, query="Northsee Ledger"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        candidates = result["preservedResults"][2]["candidates"]
        self.assertTrue(any(item["recipe_id"] == "daylight-5219" and item["matchedOn"] == "alias" for item in candidates))

    def test_unknown_query_does_not_invent_a_recipe(self):
        evidence = "p138-tc04-scene"
        result = evaluate(payload(evidenceId=evidence, query="unrelated western", repeat="scene", aliases={}))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["candidates"], [])
        self.assertEqual(len(result["preservedResults"][1]["entries"]), 5)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(query="  "))
        with self.assertRaises(ValueError):
            evaluate(payload(aliases={"not-a-recipe": ["Alias"]}))
