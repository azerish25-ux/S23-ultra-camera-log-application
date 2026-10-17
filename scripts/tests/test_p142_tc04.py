"""Tests for TC-P142-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _filters(**overrides):
    value = {"format": "35mm", "monochrome": False, "sceneFamily": "night-street"}
    value.update(overrides)
    return value


def payload(**overrides):
    catalogue = _MODULE.fixture_catalogue()
    filters = _filters()
    query = "bladrunner"
    base = {
        "evidenceId": "p142-tc04",
        "repeat": "format",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "offline": True,
        "query": query,
        "filters": filters,
        "catalogue": catalogue,
        "returned": _MODULE.local_hits(catalogue, query, filters),
        "remoteGenerationRequired": False,
        "networkUsed": False,
    }
    base.update(overrides)
    if "returned" not in overrides and (
        "query" in overrides or "filters" in overrides or "catalogue" in overrides
    ):
        base["returned"] = _MODULE.local_hits(base["catalogue"], base["query"], base["filters"])
    return base


class TCP14204(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_offline_misspelling_returns_the_local_candidate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        hits = result["preservedResults"][2]["hits"]
        self.assertEqual(hits, [{
            "id": "br",
            "match": "edit-distance",
            "evidenceStatus": "partial",
        }])
        self.assertTrue(result["preservedResults"][2]["offline"])

    def test_remote_generation_is_rejected(self):
        result = evaluate(payload(remoteGenerationRequired=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["hits"][0]["id"], "br")

    def test_network_use_is_rejected(self):
        result = evaluate(payload(networkUsed=True, repeat="monochrome"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_wrong_hit_list_is_rejected(self):
        result = evaluate(payload(returned=[]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OPAQUE_MATCH, result["rejectedClaims"])

    def test_monochrome_filter_is_a_different_local_hit(self):
        filters = _filters(monochrome=True)
        result = evaluate(payload(filters=filters, repeat="monochrome", evidenceId="p142-tc04-mono"))
        self.assert_contract(result, "p142-tc04-mono")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["hits"][0]["id"], "br-mono")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(query="!!!"))
