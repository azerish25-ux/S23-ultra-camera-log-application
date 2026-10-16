"""Tests for TC-P126-03."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p126_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"
SHA_A = hashlib.sha256(b"checkpoint-a").hexdigest()
SHA_B = hashlib.sha256(b"checkpoint-b").hexdigest()


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
        "checkpointFilename": "chunk.mp4",
        "checkpointFrame": 12,
        "checkpointSourceId": "source-a",
        "checkpointModelId": "model-a",
        "checkpointProfileId": "profile-a",
        "checkpointGraphId": "graph-a",
        "checkpointSha256": SHA_A,
        "currentFilename": "chunk.mp4",
        "currentFrame": 12,
        "currentSourceId": "source-a",
        "currentModelId": "model-a",
        "currentProfileId": "profile-a",
        "currentGraphId": "graph-a",
        "currentSha256": SHA_A,
        "resume": True,
    }
    base.update(_library())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12603(unittest.TestCase):
    def assert_contract(self, result, evidence="p126-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P126-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertTrue(result["reasons"])

    def test_matching_checkpoint_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("checkpoint-identities-match", result["reasons"])

    def test_filename_and_frame_alone_do_not_validate_resume(self):
        result = evaluate(payload(currentSourceId="source-b"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("checkpoint-identity-mismatch:source", result["rejectedClaims"])
        self.assertIn("p126-evidence", result["preservedResults"])

    def test_each_changed_identity_field_is_named(self):
        changes = {
            "source": {"currentSourceId": "source-b"},
            "model": {"currentModelId": "model-b"},
            "profile": {"currentProfileId": "profile-b"},
            "graph": {"currentGraphId": "graph-b"},
            "sha256": {"currentSha256": SHA_B},
        }
        for name, overrides in changes.items():
            with self.subTest(field=name):
                result = evaluate(payload(**overrides))
                self.assertEqual(result["decision"], "rejected")
                self.assertIn("checkpoint-identity-mismatch:" + name, result["rejectedClaims"])

    def test_mismatch_without_resume_starts_a_distinct_job(self):
        result = evaluate(payload(resume=False, currentModelId="model-b"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("distinct-job:model", result["reasons"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_playable_without_bytes_is_rejected(self):
        result = evaluate(payload(**_library(clips=[_absent_playable()])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("missing:clip-gone", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p126-profile"
        result = evaluate(payload(evidenceId=evidence, repeat="profile"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(checkpointSha256="not-a-hash"))
