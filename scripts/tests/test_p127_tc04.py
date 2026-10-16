"""Tests for TC-P127-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SRC = "a" * 64
RECIPE = "b" * 64
RESULT = "c" * 64


def manifest(**overrides):
    value = {
        "source_sha256": SRC,
        "recipe_version_sha256": RECIPE,
        "result_sha256": RESULT,
        "color_transfer": "bt709",
        "container": "mov",
        "non_claims": ["not a physical S23 qualification"],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p127-evidence",
        "repeat": "restart",
        "filename": "cancel.mov",
        "labels": ["Rec.709"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [],
        "interpretation": None,
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [],
        "stage": "rendering",
        "cancelRequested": True,
        "ownershipControlled": True,
        "cancellationAcknowledged": True,
        "publishedAsAccepted": False,
        "lateCallbackReversesCancel": False,
    }
    base.update(overrides)
    return base


class TCP12704(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_cancel_after_ownership_is_recorded_for_every_stage(self):
        for stage in ("rendering", "verification", "publication", "cleanup"):
            result = evaluate(payload(stage=stage))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded", stage)
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn("stage=" + stage, result["preservedResults"])
            self.assertIn("cancellation acknowledged after ownership", " ".join(result["reasons"]))

    def test_late_callback_is_rejected(self):
        result = evaluate(payload(lateCallbackReversesCancel=True, stage="verification"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_cancelled_job_published_as_accepted_is_rejected(self):
        result = evaluate(payload(publishedAsAccepted=True, stage="publication"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLISH_TOKEN, result["rejectedClaims"])

    def test_acknowledgement_before_ownership_is_rejected(self):
        result = evaluate(payload(ownershipControlled=False, stage="cleanup"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OWNERSHIP_TOKEN, result["rejectedClaims"])

    def test_job_that_was_not_cancelled_is_recorded(self):
        result = evaluate(payload(
            cancelRequested=False,
            cancellationAcknowledged=False,
            ownershipControlled=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("job was not cancelled", result["reasons"])

    def test_pass_through_copy_survives_a_clean_cancel(self):
        result = evaluate(payload(
            grade_applied=False,
            manifest=manifest(result_sha256=SRC),
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("pass-through copy", result["preservedResults"])

    def test_missing_non_claim_is_rejected(self):
        result = evaluate(payload(manifest=manifest(non_claims=["none"])))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-required-non-claim", result["rejectedClaims"])
        self.assertIn("p127-evidence", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(stage="accept"))
