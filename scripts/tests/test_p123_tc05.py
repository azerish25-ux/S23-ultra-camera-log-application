"""Tests for TC-P123-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p123-storage",
        "remainingBytes": 100,
        "intermediateBytes": 80,
        "publicationDuplicateBytes": 50,
        "finalOutputBytes": 40,
        "budgetedBytes": 130,
        "action": "pause",
        "jobState": "checkpointed",
        "sourceRetained": True,
        "recoverableArtifacts": True,
        "cleanupChoice": "delete-intermediates",
        "repeat": "before-rendering",
    }
    base.update(overrides)
    return base


class TCP12305(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-storage"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Temporary storage exhaustion")
        self.assertEqual(_MODULE.NEGATIVE, "Budgeting only final output bytes must fail.")
        self.assertIn("gallery publication", _MODULE.REPEAT)

    def test_pause_covers_intermediate_and_publication_bytes(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["requiredBytes"], 130)
        self.assertEqual(kept["sourceRetained"], True)
        self.assertEqual(kept["jobState"], "checkpointed")
        self.assertEqual(kept["cleanupChoice"], "delete-intermediates")

    def test_final_output_budget_and_source_loss_are_rejected(self):
        result = evaluate(
            payload(
                budgetedBytes=40,
                action="fail",
                jobState="failed",
                sourceRetained=False,
                repeat="chunk-assembly",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("budget-only-final-output-bytes", result["rejectedClaims"])
        self.assertIn("source-deleted-on-storage-failure", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["requiredBytes"], 130)
        self.assertIs(result["preservedResults"][1]["sourceRetained"], False)

    def test_continue_without_space_is_rejected_and_sufficient_space_can_continue(self):
        blocked = evaluate(payload(action="continue", jobState="running", cleanupChoice=None, repeat="gallery-publication"))
        self.assert_contract(blocked)
        self.assertEqual(blocked["decision"], "rejected")
        self.assertIn("continued-without-space", blocked["rejectedClaims"])
        clear = evaluate(
            payload(
                evidenceId="p123-storage-clear",
                remainingBytes=200,
                action="continue",
                jobState="running",
                cleanupChoice=None,
                repeat="gallery-publication",
            )
        )
        self.assert_contract(clear, "p123-storage-clear")
        self.assertEqual(clear["decision"], "recorded")
        self.assertEqual(clear["preservedResults"][1]["requiredBytes"], 130)

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(jobState="publishing"))
        with self.assertRaises(ValueError):
            evaluate(payload(remainingBytes=-1))
