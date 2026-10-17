"""Tests for TC-P138-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def edition(edition_id, appearance, stock=None, lens=None, traces=None):
    return {
        "edition_id": edition_id,
        "appearance": appearance,
        "stock": stock,
        "lens": lens,
        "traces": [] if traces is None else traces,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc06",
        "repeat": "theatrical",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "editions": [
            edition("theatrical", "warm print"),
            edition("hdr", "bright display"),
        ],
        "averagedStock": None,
        "averagedLens": None,
    }
    base.update(overrides)
    return base


class TCP13806(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_conflicting_editions_stay_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][2]
        self.assertTrue(detail["inconsistent"])
        self.assertIsNone(detail["averagedStock"])
        self.assertIsNone(detail["averagedLens"])
        self.assertEqual(
            [item["edition_id"] for item in detail["editions"]],
            ["theatrical", "hdr"],
        )
        self.assertFalse(detail["definitiveLookInvented"])

    def test_averaging_inconsistent_editions_is_rejected(self):
        result = evaluate(payload(
            repeat="HDR",
            averagedStock="5219",
            editions=[
                edition("theatrical", "warm print", stock="5219", traces=[_GATE.trace("stock", "theatrical-note")]),
                edition("digital", "cool video", stock="5207", traces=[_GATE.trace("stock", "digital-note")]),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertTrue(result["preservedResults"][2]["definitiveLookInvented"])
        self.assertIsNone(result["preservedResults"][2]["averagedStock"])
        self.assertEqual(result["preservedResults"][1]["entries"][0]["stock"], "5219")

    def test_unidentified_reference_preserves_a_different_evidence_id(self):
        evidence = "p138-tc06-unidentified"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="unidentified",
            editions=[
                edition("unidentified", "unknown display"),
                edition("digital", "unknown display"),
            ],
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][2]["inconsistent"])

    def test_unsourced_edition_stock_is_rejected(self):
        result = evaluate(payload(
            editions=[
                edition("theatrical", "same", stock="5219"),
                edition("digital", "same", stock="5219"),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNSOURCED_STOCK, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(editions=[edition("theatrical", "only one")]))
        with self.assertRaises(ValueError):
            evaluate(payload(averagedLens="   "))
