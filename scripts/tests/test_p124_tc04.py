"""Tests for TC-P124-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "stage": "verification",
        "cancellationRequested": True,
        "workerOwnsOutput": False,
        "cancellationAcknowledged": True,
        "publishedState": "withheld",
        "lateCallbackReversesCancellation": False,
        "partialRetained": True,
    }
    base.update(overrides)
    return base


class TCP12404(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_acknowledged_after_release_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("partialRetained=true", result["preservedResults"])

    def test_early_acknowledgement_is_rejected(self):
        result = evaluate(payload(workerOwnsOutput=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EARLY_ACK, result["rejectedClaims"])

    def test_accepted_publication_and_late_callback_are_rejected(self):
        result = evaluate(payload(publishedState="accepted", lateCallbackReversesCancellation=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLISHED, result["rejectedClaims"])
        self.assertIn(_MODULE.LATE_CALLBACK, result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_each_stage_can_record_a_controlled_cancellation(self):
        for stage in ("rendering", "verification", "publication", "cleanup"):
            result = evaluate(payload(stage=stage))
            self.assertEqual(result["decision"], "recorded", stage)
            self.assertIn("stage=" + stage, result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-restart"
        result = evaluate(payload(evidenceId=evidence, repeat="restart"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
