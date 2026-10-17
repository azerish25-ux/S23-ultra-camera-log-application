"""Tests for TC-P143-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc01",
        "repeat": "camera",
        "looks": _GATE.fixture_looks(),
        "dropAmbiguous": False,
        "factName": "lens",
        "factValue": None,
        "evidenceStatus": "unknown",
        "reconstructionLabel": None,
        "sourced": False,
    }
    base.update(overrides)
    return base


class TCP14301(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_removed_fact_stays_unknown_and_releases_stay_distinct(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        fact = result["preservedResults"][2]
        self.assertIsNone(fact["factValue"])
        self.assertEqual(fact["evidenceStatus"], "unknown")
        self.assertTrue(fact["keptUnknown"])
        self.assertEqual(
            result["preservedResults"][1]["distinctReleaseIds"]["reference-film"],
            ["digital-sdr", "theatrical-35mm"],
        )
        self.assertEqual(_MODULE.CASE["name"], "Missing production fact")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "plausible-guess-marked-documented")

    def test_labelled_creative_reconstruction_is_recorded(self):
        result = evaluate(payload(
            factName="stock",
            evidenceStatus="creative-reconstruction",
            reconstructionLabel="creative-reconstruction",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["reconstructionLabel"], "creative-reconstruction")

    def test_guess_marked_documented_is_rejected(self):
        result = evaluate(payload(factValue="Cooke S4", evidenceStatus="documented", sourced=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(
            result["preservedResults"][1]["distinctReleaseIds"]["reference-film"],
            ["digital-sdr", "theatrical-35mm"],
        )

    def test_sourced_fact_is_recorded(self):
        result = evaluate(payload(
            factName="camera",
            factValue="Panavision Panaflex",
            evidenceStatus="documented",
            sourced=True,
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["factValue"], "Panavision Panaflex")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc01-process"
        result = evaluate(payload(evidenceId=evidence, repeat="process", factName="process"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(factName="director"))
