"""Tests for TC-P122-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc04",
        "repeat": "Repeat with process restart and an already retained partial output.",
        "stage": "rendering",
        "cancelled": True,
        "ownershipControlled": True,
        "acknowledged": True,
        "publishedAsAccepted": False,
        "lateCallbackReversesCancellation": False,
        "versions": _MODULE.valid_versions(),
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12204(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_owned_cancellation_is_recorded_not_qualified(self):
        result = evaluate(payload(stage="verification"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stage=verification", result["preservedResults"])

    def test_late_callback_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(lateCallbackReversesCancellation=True, stage="publication"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_cancelled_job_published_as_accepted_is_rejected(self):
        result = evaluate(payload(publishedAsAccepted=True, stage="cleanup"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLISHED_TOKEN, result["rejectedClaims"])

    def test_acknowledgement_without_ownership_is_rejected(self):
        result = evaluate(payload(ownershipControlled=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OWNERSHIP_TOKEN, result["rejectedClaims"])

    def test_recipe_hash_mismatch_is_rejected(self):
        versions = _MODULE.valid_versions()
        versions[1]["version_sha256"] = "e" * 64
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("version-sha256-mismatch", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc04-restart"
        result = evaluate(payload(evidenceId=evidence, repeat="process restart"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(stage="encoding"))
