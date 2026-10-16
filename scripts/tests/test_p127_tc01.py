"""Tests for TC-P127-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc01.py",
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
        "color_transfer": "logc3",
        "container": "mov",
        "non_claims": ["not a physical S23 qualification"],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p127-evidence",
        "repeat": "portrait",
        "filename": "portrait.mov",
        "labels": ["LogC3"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [],
        "interpretation": {"transfer": "logc3", "note": "scene-referred LogC3"},
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [],
        "detectedColorTags": ["logc3"],
        "detectedRotation": 90,
        "detectedFrameRate": 24,
        "timingVariable": False,
        "userTransfer": None,
        "userDynamicRange": None,
        "importerTransfer": None,
        "importerDynamicRange": None,
        "userOverride": False,
    }
    base.update(overrides)
    return base


class TCP12701(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("detected-facts-separated-from-user-interpretation", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_detected_portrait_tag_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("detectedRotation=90", result["reasons"])
        self.assertIn("filenameExtension=mov is not a transfer", result["reasons"])

    def test_extension_alone_is_rejected(self):
        result = evaluate(payload(
            detectedColorTags=[],
            detectedRotation=None,
            detectedFrameRate=None,
            importerTransfer="bt709",
            importerDynamicRange="sdr",
            filename="untagged.mp4",
            labels=["untagged"],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_explicit_user_interpretation_is_kept_separate(self):
        result = evaluate(payload(
            detectedColorTags=[],
            userTransfer="hlg",
            userDynamicRange="hdr",
            importerTransfer="hlg",
            importerDynamicRange="hdr",
            userOverride=True,
            repeat="hdr-looking",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("userTransfer=hlg", result["reasons"])
        self.assertIn("explicit user interpretation was not inferred from the filename extension", result["reasons"])

    def test_contradictory_tags_are_not_collapsed(self):
        unresolved = evaluate(payload(detectedColorTags=["bt709", "hlg"], importerTransfer=None))
        self.assert_contract(unresolved)
        self.assertEqual(unresolved["decision"], "recorded")
        self.assertIn("contradictory detected facts left unresolved", unresolved["reasons"])
        collapsed = evaluate(payload(detectedColorTags=["bt709", "hlg"], importerTransfer="bt709"))
        self.assertEqual(collapsed["decision"], "rejected")
        self.assertIn(_MODULE.CONTRADICTION_TOKEN, collapsed["rejectedClaims"])

    def test_silent_normalization_is_rejected(self):
        result = evaluate(payload(importerTransfer="hlg"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SILENT_TOKEN, result["rejectedClaims"])

    def test_variable_rate_stays_a_detected_fact(self):
        result = evaluate(payload(timingVariable=True, detectedFrameRate=23.976, repeat="variable"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("timingVariable=true", result["reasons"])

    def test_false_log_relabel_is_rejected_with_evidence(self):
        result = evaluate(payload(
            manifest=manifest(color_transfer="bt709"),
            labels=["LogC3"],
            filename="relabel.mov",
            interpretation=None,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-transfer-relabelled-as-log", result["rejectedClaims"])
        self.assertIn("p127-evidence", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        result = evaluate(payload(evidenceId="p127-untagged", repeat="untagged", detectedColorTags=[]))
        self.assert_contract(result, "p127-untagged")
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("ambiguous import left unresolved; no assumed source type", result["reasons"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(detectedFrameRate=0))
