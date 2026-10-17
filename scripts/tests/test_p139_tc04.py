"""Tests for TC-P139-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def catalogue(fact_hash: str):
    return [
        {
            "title": "Night Ferry",
            "alternateTitles": ["Le Bac de Nuit"],
            "stock": "Kodak Vision3 250D",
            "format": "35mm",
            "monochrome": False,
            "sceneFamily": "day-exterior",
            "evidenceStatus": "partial",
            "fact_hash": fact_hash,
        },
        {
            "title": "Night Ferry",
            "alternateTitles": ["Night Ferry Archive"],
            "stock": "Eastman Double-X",
            "format": "16mm",
            "monochrome": True,
            "sceneFamily": "archive",
            "evidenceStatus": "documented",
            "fact_hash": fact_hash,
        },
        {
            "title": "Glass Hotel",
            "alternateTitles": ["Hotel de Verre"],
            "stock": "Kodak Vision3 500T",
            "format": "35mm",
            "monochrome": False,
            "sceneFamily": "night-interior",
            "evidenceStatus": "documented",
            "fact_hash": "ab" * 32,
        },
    ]


def payload(**overrides):
    bundle = _MODULE._CORE.bundle_for()
    base = {
        "evidenceId": "p139-tc04",
        "repeat": "format",
        "query": "Night Fery",
        "catalogue": catalogue(bundle["fact_hash"]),
        "filter": {"format": "35mm"},
        "networkAvailable": False,
        "remoteGenerationCalled": False,
    }
    base.update(bundle)
    base.update(overrides)
    return base


class TCP13904(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_offline_typo_returns_local_evidence_status(self):
        body = payload()
        result = evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("candidateCount=1", result["preservedResults"])
        self.assertTrue(
            any(
                item.startswith("candidate=Night Ferry match=typo-title evidence=partial fact_hash=")
                for item in result["preservedResults"]
            )
        )
        self.assertIn(body["fact_hash"], " ".join(result["preservedResults"]))

    def test_monochrome_and_scene_family_filters(self):
        mono = evaluate(
            payload(repeat="monochrome", filter={"monochrome": True}, evidenceId="p139-tc04-mono")
        )
        self.assert_contract(mono, "p139-tc04-mono")
        self.assertEqual(mono["decision"], "recorded")
        self.assertIn("evidence=documented", " ".join(item for item in mono["preservedResults"] if item.startswith("candidate=")))
        family = evaluate(payload(repeat="scene-family", filter={"sceneFamily": "archive"}))
        self.assertEqual(family["decision"], "recorded")
        self.assertIn("candidateCount=1", family["preservedResults"])

    def test_remote_generation_is_rejected(self):
        result = evaluate(payload(remoteGenerationCalled=True, networkAvailable=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("candidateCount=1", result["preservedResults"])
        self.assertIn("p139-tc04", result["preservedResults"])

    def test_alternate_title_and_stock_match_without_network(self):
        alternate = evaluate(payload(query="Le Bac de Nuit"))
        self.assertEqual(alternate["decision"], "recorded")
        self.assertIn("match=exact-title", " ".join(alternate["preservedResults"]))
        stock = evaluate(payload(query="Double-X", repeat="format", filter={"format": "16mm"}))
        self.assertEqual(stock["decision"], "recorded")
        self.assertIn("match=stock-name", " ".join(stock["preservedResults"]))

    def test_mutated_facts_are_rejected(self):
        result = evaluate(payload(mutated_facts=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(query=" "))
