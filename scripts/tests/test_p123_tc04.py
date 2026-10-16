"""Tests for TC-P123-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p123-cancel",
        "phaseAtCancel": "verification",
        "transitionLog": ["idle", "queued", "running", "cancelled"],
        "terminalState": "cancelled",
        "sourceRetained": True,
        "workersReleased": True,
        "lateCallback": None,
        "publishedAccepted": False,
        "partialRetained": True,
        "repeat": "process-restart",
    }
    base.update(overrides)
    return base


class TCP12304(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-cancel"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Cancellation at acceptance boundary")
        self.assertEqual(
            _MODULE.EXPECTED,
            "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "A late worker callback that reverses cancellation must fail.")
        self.assertIn("retained partial output", _MODULE.REPEAT)

    def test_released_cancel_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1], ["idle", "queued", "running", "cancelled"])
        self.assertTrue(result["preservedResults"][3]["sourceRetained"])
        self.assertTrue(result["preservedResults"][3]["workersReleased"])
        self.assertFalse(result["preservedResults"][3]["publishedAccepted"])

    def test_late_callback_and_accepted_publish_are_rejected(self):
        result = evaluate(payload(lateCallback="completed", publishedAccepted=True, repeat="retained-partial-output"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("late-worker-reverses-cancellation", result["rejectedClaims"])
        self.assertIn("cancelled-job-published-as-accepted", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][2], "cancelled")
        self.assertEqual(result["preservedResults"][3]["lateCallback"], "completed")

    def test_source_loss_and_owned_handles_are_rejected(self):
        result = evaluate(payload(sourceRetained=False, workersReleased=False, phaseAtCancel="rendering"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("source-not-retained-on-cancel", result["rejectedClaims"])
        self.assertIn("cancellation-before-workers-released", result["rejectedClaims"])
        self.assertIs(result["preservedResults"][3]["sourceRetained"], False)

    def test_skipping_queued_to_completed_is_rejected(self):
        result = evaluate(
            payload(
                transitionLog=["idle", "queued", "completed"],
                terminalState="completed",
                phaseAtCancel="publication",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("skipped-queued-to-completed", result["rejectedClaims"])
        self.assertIn("cancellation-not-terminal", result["rejectedClaims"])

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(lateCallback="publishing"))
        with self.assertRaises(ValueError):
            evaluate(payload(transitionLog=["idle", "verifying", "cancelled"], terminalState="cancelled"))
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="retained-partial-output", partialRetained=False))
