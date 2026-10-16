"""Tests for TC-P121-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-cancel",
        "repeat": "retained-partial",
        "stage": "rendering",
        "cancelRequested": True,
        "ownershipControlled": True,
        "acknowledged": True,
        "lateCallbackReversesCancel": False,
        "publishedAsAccepted": False,
        "partialOutputRetained": True,
    }
    base.update(overrides)
    return base


class TCP12104(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-cancel"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Cancellation at acceptance boundary")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Cancel during rendering, verification, publication, or final cleanup.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "A late worker callback that reverses cancellation must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat with process restart and an already retained partial output.",
        )

    def test_owned_cancel_is_recorded_and_not_accepted(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertTrue(kept["acknowledged"])
        self.assertFalse(kept["publishedAsAccepted"])
        self.assertTrue(kept["partialOutputRetained"])

    def test_late_callback_and_accepted_publish_are_rejected(self):
        late = evaluate(payload(repeat="process-restart", lateCallbackReversesCancel=True, partialOutputRetained=False))
        self.assert_contract(late)
        self.assertEqual(late["decision"], "rejected")
        self.assertIn(_MODULE.LATE_TOKEN, late["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, late["reasons"])
        published = evaluate(payload(stage="publication", publishedAsAccepted=True))
        self.assertEqual(published["decision"], "rejected")
        self.assertIn("cancelled-job-published-as-accepted", published["rejectedClaims"])
        self.assertFalse(published["preservedResults"][1]["publishedAsAccepted"])

    def test_acknowledgement_requires_ownership(self):
        result = evaluate(payload(stage="verification", ownershipControlled=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("cancellation-acknowledged-before-ownership", result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["acknowledged"])
        cleanup = evaluate(payload(stage="final-cleanup", partialOutputRetained=True))
        self.assertEqual(cleanup["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(stage="encode"))
        with self.assertRaises(ValueError):
            evaluate(payload(cancelRequested="yes"))
