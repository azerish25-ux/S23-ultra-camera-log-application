"""Tests for TC-P126-08."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p126_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"
PRIVATE = "/storage/emulated/0/DCIM/Camera/private_clip.mov"
INTERPRETATION = {"transfer": "logc3", "ei": 800}


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
        "paths": ["take.mov"],
        "masterKind": "log",
        "interpretation": dict(INTERPRETATION),
        "presentedAsSelfDescribing": False,
        "recipeRetained": True,
    }
    base.update(_library())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"] + result["rejectedClaims"])


class TCP12608(unittest.TestCase):
    def assert_contract(self, result, evidence="p126-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P126-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertTrue(result["reasons"])

    def test_log_master_with_interpretation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        canonical = json.dumps(INTERPRETATION, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        token = "interpretationSha256=" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.assertIn(token, result["preservedResults"])
        self.assertIn("interpretation-retained", result["reasons"])
        self.assertIn("path=take.mov", result["preservedResults"])

    def test_log_master_without_interpretation_is_rejected(self):
        result = evaluate(payload(interpretation=None, presentedAsSelfDescribing=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p126-evidence", result["preservedResults"])

    def test_private_path_is_redacted(self):
        result = evaluate(payload(paths=[PRIVATE], masterKind="sdr", interpretation=None))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        digest = hashlib.sha256(PRIVATE.encode("utf-8")).hexdigest()
        self.assertIn("redactedPathSha256=" + digest, result["preservedResults"])
        self.assertNotIn(PRIVATE, blob(result))

    def test_hdr_without_signal_interpretation_is_rejected(self):
        result = evaluate(payload(masterKind="hdr-derived", interpretation=None))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HDR_TOKEN, result["rejectedClaims"])

    def test_partial_export_is_not_self_describing(self):
        recorded = evaluate(payload(masterKind="partial", interpretation=None, presentedAsSelfDescribing=False))
        self.assert_contract(recorded)
        self.assertEqual(recorded["decision"], "recorded")
        self.assertIn("partial-export-not-self-describing", recorded["reasons"])
        rejected = evaluate(payload(masterKind="partial", interpretation=None, presentedAsSelfDescribing=True))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_MODULE.PARTIAL_TOKEN, rejected["rejectedClaims"])

    def test_playable_without_bytes_is_rejected(self):
        result = evaluate(payload(**_library(clips=[_absent_playable()])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("missing:clip-gone", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p126-sdr"
        result = evaluate(payload(evidenceId=evidence, repeat="sdr", masterKind="sdr", interpretation=None))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(masterKind="raw"))
