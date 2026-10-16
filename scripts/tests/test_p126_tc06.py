"""Tests for TC-P126-06."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p126_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"
HISTORICAL = "source-sha-kept-after-revoke"


def _verified():
    content = "paired-result"
    encoded = content.encode("utf-8")
    return {
        "clip_id": "clip-result",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": True,
        "playable": True,
        "verification": "verified",
        "content": content,
        "role": "result",
        "bundle_id": "take-1",
    }


def _revoked():
    encoded = b"p126-revoked-source-v1"
    return {
        "clip_id": "clip-source",
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
        "byte_count": len(encoded),
        "present": False,
        "playable": False,
        "verification": "missing",
        "thumbnail_cached": True,
        "role": "source",
        "bundle_id": "take-1",
    }


def _library(clips=None, omitted=None):
    default = [_revoked(), _verified()]
    return {
        "clips": default if clips is None else clips,
        "omitted_ids": ["clip-source"] if omitted is None else omitted,
    }


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
        "access": "local",
        "grantRevoked": True,
        "sourceClipId": "clip-source",
        "thumbnailCached": True,
        "treatsThumbnailAsMedia": False,
        "historicalMetadata": HISTORICAL,
    }
    base.update(_library())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12606(unittest.TestCase):
    def assert_contract(self, result, evidence="p126-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P126-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn(HISTORICAL, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertTrue(result["reasons"])

    def test_revoked_source_with_cached_thumbnail_is_recorded_as_unavailable(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("missing:clip-source", result["preservedResults"])
        self.assertIn("thumbnail-cached-not-media:clip-source", result["reasons"])
        self.assertIn("thumbnail-not-availability:clip-source", result["reasons"])
        self.assertIn("access=local", result["reasons"])

    def test_thumbnail_does_not_certify_media(self):
        result = evaluate(payload(treatsThumbnailAsMedia=True, access="document-provider"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("missing:clip-source", result["preservedResults"])

    def test_revoked_grant_left_available_is_rejected(self):
        source = _revoked()
        source.update({"present": True, "playable": True, "verification": "verified", "content": "p126-revoked-source-v1"})
        result = evaluate(payload(
            clips=[source, _verified()],
            thumbnailCached=False,
            access="recovered",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REVOKED_TOKEN, result["rejectedClaims"])

    def test_index_that_drops_a_known_missing_id_is_rejected(self):
        result = evaluate(payload(omitted_ids=["clip-source", "clip-dropped"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("omitted-missing-id:clip-dropped", result["rejectedClaims"])
        self.assertIn("missing:clip-source", result["preservedResults"])

    def test_playable_without_bytes_is_rejected(self):
        gone = _absent_playable()
        result = evaluate(payload(
            sourceClipId="clip-gone",
            thumbnailCached=False,
            clips=[gone],
            omitted_ids=["clip-gone"],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("missing:clip-gone", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p126-recovered"
        result = evaluate(payload(evidenceId=evidence, repeat="recovered", access="recovered"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(access="cloud"))
