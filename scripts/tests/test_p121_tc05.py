"""Tests for TC-P121-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-storage",
        "repeat": "before-rendering",
        "remainingBytes": 500,
        "intermediateBytes": 100,
        "duplicatePublicationBytes": 50,
        "finalOutputBytes": 40,
        "budgetedBytes": 200,
        "sourcePreserved": True,
        "recoverableArtifacts": ["source-copy"],
    }
    base.update(overrides)
    return base


class TCP12105(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-storage"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Temporary storage exhaustion")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Make remaining space insufficient for intermediate work or duplicate publication storage.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Pause or fail safely before source loss, preserving recoverable artifacts and clear cleanup choices.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Budgeting only final output bytes must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat before rendering, during chunk assembly, and during gallery publication.",
        )

    def test_budget_that_covers_intermediates_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["requiredBytes"], 150)
        self.assertTrue(result["preservedResults"][1]["sourcePreserved"])

    def test_final_output_budget_is_rejected(self):
        result = evaluate(
            payload(
                repeat="chunk-assembly",
                remainingBytes=10,
                budgetedBytes=40,
                recoverableArtifacts=["chunk-0"],
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["budgetedBytes"], 40)
        self.assertEqual(result["preservedResults"][1]["requiredBytes"], 150)
        self.assertIn("chunk-0", result["preservedResults"][1]["recoverableArtifacts"])

    def test_safe_pause_keeps_the_source(self):
        paused = evaluate(
            payload(
                repeat="gallery-publication",
                remainingBytes=10,
                recoverableArtifacts=["gallery-partial"],
            )
        )
        self.assertEqual(paused["decision"], "recorded")
        self.assertTrue(any("paused-or-failed-before-source-loss" in item for item in paused["reasons"]))
        self.assertIn("gallery-partial", paused["preservedResults"][1]["recoverableArtifacts"])
        lost = evaluate(payload(sourcePreserved=False, recoverableArtifacts=["leftover"]))
        self.assertEqual(lost["decision"], "rejected")
        self.assertIn("source-loss", lost["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(remainingBytes=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(recoverableArtifacts=[""]))
