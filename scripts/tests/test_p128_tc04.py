"""Tests for TC-P128-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _long_form(**overrides):
    value = {
        "expected_frames": 6,
        "accounted_frames": [0, 1, 2, 3, 4, 5],
        "checkpoint_frames": [0, 2, 5],
        "audio_duration": 0.25,
        "video_duration": 0.25,
        "audio_absent": False,
        "spot_check_only": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p128-evidence",
        "repeat": "Repeat",
        "stage": "publication",
        "cancelRequested": False,
        "ownershipControlled": True,
        "cancelAcknowledged": False,
        "callbackAccepts": False,
        "published": True,
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12804(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frameAccount=", blob(result))
        self.assertTrue(result["reasons"])

    def test_publication_without_cancellation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("publication kept; no cancellation to reverse", result["reasons"])

    def test_cancellation_after_ownership_is_recorded(self):
        result = evaluate(payload(
            stage="rendering",
            cancelRequested=True,
            ownershipControlled=True,
            cancelAcknowledged=True,
            callbackAccepts=False,
            published=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("cancellation acknowledged after ownership was controlled", result["reasons"])

    def test_late_callback_is_rejected(self):
        result = evaluate(payload(
            stage="verification",
            cancelRequested=True,
            ownershipControlled=True,
            cancelAcknowledged=True,
            callbackAccepts=True,
            published=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_cancelled_job_is_not_published(self):
        result = evaluate(payload(
            stage="cleanup",
            cancelRequested=True,
            cancelAcknowledged=True,
            published=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLISH_TOKEN, result["rejectedClaims"])

    def test_acknowledgement_before_ownership_is_rejected(self):
        result = evaluate(payload(
            stage="rendering",
            cancelRequested=True,
            ownershipControlled=False,
            cancelAcknowledged=True,
            published=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OWNERSHIP_TOKEN, result["rejectedClaims"])

    def test_duplicate_frame_is_rejected_inside_the_case(self):
        result = evaluate(payload(accounted_frames=[0, 1, 2, 3, 4, 5, 1]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-restart"
        result = evaluate(payload(evidenceId=evidence, repeat="restart"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
