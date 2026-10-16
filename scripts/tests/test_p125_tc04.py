"""Tests for TC-P125-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p125-cancel",
        "repeat": "process-restart",
        "stage": "rendering",
        "ownershipControlled": True,
        "cancellationAcknowledged": True,
        "publishedAsAccepted": False,
        "lateCallbackReversesCancellation": False,
        "partialOutputRetained": True,
    }
    base.update(overrides)
    return base


class TCP12504(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-cancel"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Cancellation at acceptance boundary")
        self.assertEqual(_MODULE.NEGATIVE, "A late worker callback that reverses cancellation must fail.")
        self.assertEqual(_MODULE.REPEAT, "Repeat with process restart and an already retained partial output.")

    def test_owned_cancellation_is_recorded_and_keeps_the_partial(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["partialOutputRetained"])
        self.assertFalse(result["preservedResults"][1]["publishedAsAccepted"])

    def test_late_callback_is_rejected(self):
        result = evaluate(payload(lateCallbackReversesCancellation=True, stage="publication"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LATE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertTrue(result["preservedResults"][1]["partialOutputRetained"])

    def test_published_cancel_and_early_ack_are_rejected(self):
        result = evaluate(
            payload(
                repeat="retained-partial-output",
                stage="final-cleanup",
                ownershipControlled=False,
                cancellationAcknowledged=True,
                publishedAsAccepted=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLISHED_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.EARLY_TOKEN, result["rejectedClaims"])

    def test_ack_waits_for_ownership(self):
        result = evaluate(
            payload(evidenceId="p125-wait", stage="verification", ownershipControlled=False, cancellationAcknowledged=False)
        )
        self.assert_contract(result, "p125-wait")
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(stage="cleanup"))
