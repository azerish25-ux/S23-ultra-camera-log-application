"""Tests for TC-P140-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def editions():
    return [
        {"editionId": "theatrical-print", "release": "theatrical", "display": "projection", "appearance": "silver print"},
        {"editionId": "digital-master", "release": "digital", "display": "rec709", "appearance": "video master"},
        {"editionId": "hdr-pass", "release": "HDR", "display": "pq", "appearance": "hdr grade"},
        {"editionId": "unknown-ref", "release": "unidentified", "display": "unidentified", "appearance": "unidentified"},
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p140-tc06",
        "repeat": "theatrical",
        "title": "Night Hunter",
        "editions": editions(),
        "averagedIntoSingleFact": False,
    }
    base.update(overrides)
    return base


class TCP14006(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_separate_editions_are_recorded_in_id_order(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(
            kept["editionIds"],
            ["digital-master", "hdr-pass", "theatrical-print", "unknown-ref"],
        )
        self.assertFalse(kept["averagedIntoSingleFact"])
        self.assertTrue(kept["uncertaintyKept"])

    def test_averaging_inconsistent_editions_is_rejected(self):
        result = evaluate(payload(averagedIntoSingleFact=True, repeat="HDR"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("unknown-ref", result["preservedResults"][1]["editionIds"])
        self.assertNotIn("averaged-look", result["preservedResults"][1]["editionIds"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p140-tc06-unidentified"
        result = evaluate(payload(evidenceId=evidence, repeat="unidentified reference versions"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(editions=editions()[:1]))
