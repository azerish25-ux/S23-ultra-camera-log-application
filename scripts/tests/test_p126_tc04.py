"""Tests for TC-P126-04."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p126_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"


def _library(clips=None, omitted=None):
    content = "paired-result"
    encoded = content.encode("utf-8")
    default = [{
        "clip_id": "clip-result",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": True,
        "playable": True,
        "verification": "verified",
        "content": content,
        "role": "result",
        "bundle_id": "take-1",
    }]
    return {"clips": default if clips is None else clips, "omitted_ids": [] if omitted is None else omitted}


def _absent_playable():
    encoded = b"gone"
    return {
        "clip_id": "clip-gone",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": False,
        "playable": True,
        "verification": "missing",
    }


def payload(**overrides):
    base = {
        "evidenceId": "p126-evidence",
        "repeat": "Repeat",
        "stage": "publication",
        "cancellationRequested": True,
        "ownershipControlled": True,
        "cancellationAcknowledged": True,
        "publishedAsAccepted": False,
        "lateCallbackReverses": False,
    }
    base.update(_library())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12604(unittest.TestCase):
    def assert_contract(self, result, evidence="p126-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P126-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertTrue(result["reasons"])

    def test_owned_cancellation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("cancellation-acknowledged-after-ownership", result["reasons"])

    def test_late_callback_cannot_reverse_cancellation(self):
        result = evaluate(payload(lateCallbackReverses=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p126-evidence", result["preservedResults"])

    def test_cancelled_job_is_not_published_as_accepted(self):
        result = evaluate(payload(publishedAsAccepted=True, stage="cleanup"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLISHED_TOKEN, result["rejectedClaims"])

    def test_acknowledgement_without_ownership_is_rejected(self):
        result = evaluate(payload(ownershipControlled=False, stage="rendering"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OWNERSHIP_TOKEN, result["rejectedClaims"])

    def test_playable_without_bytes_is_rejected(self):
        result = evaluate(payload(**_library(clips=[_absent_playable()])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("missing:clip-gone", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p126-restart"
        result = evaluate(payload(evidenceId=evidence, repeat="restart", stage="verification"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(stage="encode"))
