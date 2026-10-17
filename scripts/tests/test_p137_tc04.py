"""Tests for TC-P137-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def filters(fmt=None, monochrome=None, scene_family=None):
    return {"format": fmt, "monochrome": monochrome, "sceneFamily": scene_family}


def payload(**overrides):
    base = {
        "evidenceId": "p137-tc04",
        "repeat": "title",
        "query": "Nortwater",
        "filters": filters(),
        "remoteRequired": False,
    }
    base.update(overrides)
    return base


class TCP13704(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_misspelling_returns_local_candidate_with_evidence_status(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertFalse(detail["networkUsed"])
        self.assertEqual(detail["candidates"][0]["id"], "northwater")
        self.assertEqual(detail["candidates"][0]["matchedOn"], "title")
        self.assertGreater(detail["candidates"][0]["distance"], 0)
        self.assertLessEqual(detail["candidates"][0]["distance"], 2)
        self.assertEqual(detail["candidates"][0]["evidenceStatus"]["lens"], "unknown")
        self.assertEqual(detail["candidates"][0]["evidenceStatus"]["stock"], "fact")
        self.assertEqual(detail["candidates"][0]["evidenceStatus"]["virtual_lens"], "reconstruction")
        self.assertFalse(detail["candidates"][0]["networkUsed"])
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Offline search ambiguity")

    def test_alternate_title_and_stock_match_locally(self):
        alternate = evaluate(payload(query="Lamp of the Noth", repeat="alternate title"))
        self.assertEqual(alternate["decision"], "recorded")
        self.assertEqual(alternate["preservedResults"][1]["candidates"][0]["matchedOn"], "alternateTitle")
        stock = evaluate(payload(query="5293", repeat="stock"))
        self.assertEqual(stock["decision"], "recorded")
        ids = {item["id"] for item in stock["preservedResults"][1]["candidates"]}
        self.assertIn("northwater", ids)
        self.assertTrue(all(item["networkUsed"] is False for item in stock["preservedResults"][1]["candidates"]))

    def test_filters_cover_format_monochrome_and_scene_family(self):
        monochrome = evaluate(payload(
            query="Glass Orchard",
            filters=filters(monochrome=True),
            repeat="monochrome",
        ))
        self.assertEqual(monochrome["decision"], "recorded")
        self.assertEqual([item["id"] for item in monochrome["preservedResults"][1]["candidates"]], ["glass-orchard"])
        formatted = evaluate(payload(
            query="Glass Orchard",
            filters=filters(fmt="16mm"),
            repeat="format",
        ))
        self.assertEqual(formatted["preservedResults"][1]["candidates"][0]["id"], "glass-orchard")
        family = evaluate(payload(
            query="Northwater",
            filters=filters(scene_family="night-interior"),
            repeat="scene family",
        ))
        self.assertEqual(family["decision"], "recorded")
        self.assertEqual(family["preservedResults"][1]["candidates"][0]["id"], "northwater")
        self.assertEqual(family["preservedResults"][1]["candidates"][0]["distance"], 0)

    def test_remote_generation_is_rejected_without_using_the_network(self):
        result = evaluate(payload(remoteRequired=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.REMOTE_REQUIRED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        detail = result["preservedResults"][1]
        self.assertFalse(detail["networkUsed"])
        self.assertFalse(detail["candidates"][0]["networkUsed"])
        self.assertEqual(detail["candidates"][0]["id"], "northwater")
        self.assertIn("p137-tc04", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(query="no"))
