"""Tests for TC-P140-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p140-tc01",
        "repeat": "lens",
        "recordId": "movie-a",
        "title": "Night Hunter",
        "facts": {
            "camera": "Panavision Panaflex",
            "lens": "unknown",
            "stock": "Eastman Double-X",
            "process": "photochemical",
            "releaseVersion": "theatrical",
        },
        "documented": ["camera", "stock", "process", "releaseVersion"],
        "guessField": "lens",
        "guessValue": "50mm spherical",
        "creativeReconstruction": True,
        "reconstructionLabel": "creative reconstruction",
    }
    base.update(overrides)
    return base


class TCP14001(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unknown_lens_with_labelled_reconstruction_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["factValue"], "unknown")
        self.assertEqual(kept["searchIds"], ["movie-a"])
        self.assertEqual(kept["reconstruction"]["value"], "50mm spherical")
        self.assertFalse(kept["reconstruction"]["documented"])
        self.assertEqual(_MODULE.CASE["name"], "Missing production fact")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "plausible-equipment-guess-marked-documented")

    def test_guess_marked_documented_is_rejected_and_fact_stays_unknown(self):
        result = evaluate(payload(documented=["camera", "lens", "stock", "process", "releaseVersion"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["factValue"], "unknown")
        self.assertIsNone(result["preservedResults"][1]["reconstruction"])

    def test_writing_the_guess_into_the_fact_is_rejected(self):
        facts = payload()["facts"]
        facts["stock"] = "Kodak Vision3"
        result = evaluate(payload(facts=facts, guessField="stock", guessValue="Kodak Vision3", repeat="stock"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OVERWROTE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p140-tc01-process"
        result = evaluate(payload(evidenceId=evidence, repeat="process", guessField="process", creativeReconstruction=False, reconstructionLabel=""))
        facts = payload()["facts"]
        facts["process"] = "unknown"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="process",
            facts=facts,
            documented=["camera", "lens", "stock", "releaseVersion"],
            guessField="process",
            guessValue="bleach bypass",
            creativeReconstruction=False,
            reconstructionLabel="",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["factValue"], "unknown")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(guessField="director"))
