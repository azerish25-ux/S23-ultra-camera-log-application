"""Tests for TC-P126-01."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p126_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p126_tc01.py",
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
        "filename": "portrait-untagged.mov",
        "colorTag": None,
        "containerTransfer": None,
        "rotationDegrees": 90,
        "timingRate": None,
        "declaredTransfer": None,
        "declaredDynamicRange": None,
        "userInterpretation": "operator-thinks-hlg",
    }
    base.update(_library())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12601(unittest.TestCase):
    def assert_contract(self, result, evidence="p126-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P126-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("playableRule=" + RULE, blob(result))
        self.assertTrue(result["reasons"])

    def test_untagged_import_keeps_facts_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("detected.color_tag=absent", result["preservedResults"])
        self.assertIn("user_interpretation=operator-thinks-hlg", result["preservedResults"])
        self.assertIn("extension=mov extension-not-used-for-transfer", result["reasons"])
        self.assertIn("detected.rotation=90", result["reasons"])
        self.assertIn("detected.timing=unspecified", result["reasons"])

    def test_filename_extension_does_not_assign_transfer(self):
        result = evaluate(payload(declaredTransfer="rec709", declaredDynamicRange="hdr"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p126-evidence", result["preservedResults"])

    def test_contradictory_tags_are_not_normalized(self):
        result = evaluate(payload(
            colorTag="rec709",
            containerTransfer="hlg",
            userInterpretation=None,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CONTRADICTION_TOKEN, result["rejectedClaims"])
        self.assertIn("detected.color_tag=rec709", result["reasons"])
        self.assertIn("detected.container_transfer=hlg", result["reasons"])
        self.assertNotIn(_MODULE.SILENT_TOKEN, result["rejectedClaims"])

    def test_detected_hlg_tag_can_be_recorded_at_a_fractional_rate(self):
        result = evaluate(payload(
            filename="portrait.mov",
            colorTag="hlg",
            containerTransfer="hlg",
            declaredTransfer="hlg",
            declaredDynamicRange="hdr",
            timingRate=23.976,
            userInterpretation=None,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("detected.timing=23.976", result["reasons"])

    def test_playable_without_bytes_is_rejected(self):
        result = evaluate(payload(**_library(clips=[_absent_playable()])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playable-absent-bytes", result["rejectedClaims"])
        self.assertIn("missing:clip-gone", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p126-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
