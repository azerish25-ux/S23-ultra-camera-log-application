"""Tests for TC-P127-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SRC = "a" * 64
RECIPE = "b" * 64
RESULT = "c" * 64
PRIVATE = "/home/ada/Movies/private_take.mov"
EMAIL = "ada@example.com"


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
        "repeat": "clean-log",
        "filename": "share_LogC3.mov",
        "labels": ["LogC3"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [f"owner={EMAIL} source={PRIVATE} color_transfer=logc3"],
        "interpretation": {"transfer": "logc3", "note": "scene-referred LogC3 EI800"},
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [EMAIL],
        "shareKind": "log-master",
        "verificationSummaryPresent": True,
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12708(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_clean_log_share_is_redacted_and_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        text = blob(result)
        self.assertIn("[redacted-path]", text)
        self.assertIn("[redacted-identifier]", text)
        self.assertIn("source_sha256=" + SRC, result["preservedResults"])
        self.assertIn("color_transfer=logc3", result["preservedResults"])
        self.assertIn("not a physical S23 qualification", text)
        self.assertNotIn(PRIVATE, text)
        self.assertNotIn(EMAIL, text)
        self.assertIn("technical interpretation retained for the share", result["reasons"])

    def test_log_master_without_interpretation_is_rejected(self):
        result = evaluate(payload(
            interpretation=None,
            selfDescribing=True,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source_sha256=" + SRC, result["preservedResults"])

    def test_rendered_sdr_is_recorded_until_it_is_relabelled_log(self):
        clean = evaluate(payload(
            shareKind="rendered-sdr",
            manifest=manifest(color_transfer="bt709"),
            labels=["Rec.709"],
            filename="delivery.mov",
            interpretation=None,
            metadataTexts=["color_transfer=bt709"],
            personalIdentifiers=[],
            repeat="sdr",
        ))
        self.assertEqual(clean["decision"], "recorded")
        relabel = evaluate(payload(
            shareKind="rendered-sdr",
            manifest=manifest(color_transfer="bt709"),
            labels=["Log"],
            filename="delivery.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(relabel["decision"], "rejected")
        self.assertIn("display-transfer-relabelled-as-log", relabel["rejectedClaims"])

    def test_hdr_derived_look_is_recorded(self):
        result = evaluate(payload(
            shareKind="hdr-derived",
            manifest=manifest(color_transfer="hlg"),
            labels=["HLG"],
            filename="hdr.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
            repeat="hdr",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_unverified_partial_is_not_a_complete_share(self):
        held = evaluate(payload(
            shareKind="unverified-partial",
            export_allowed=False,
            manifest=manifest(color_transfer="bt709"),
            labels=["Rec.709"],
            filename="partial.mov",
            interpretation=None,
            verificationSummaryPresent=False,
            metadataTexts=[],
            personalIdentifiers=[],
            repeat="partial",
        ))
        self.assertEqual(held["decision"], "recorded")
        self.assertIn("unverified partial export kept out of the default verified share", held["reasons"])
        exported = evaluate(payload(
            shareKind="unverified-partial",
            manifest=manifest(color_transfer="bt709"),
            labels=["Rec.709"],
            filename="partial.mov",
            interpretation=None,
            verificationSummaryPresent=False,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(exported["decision"], "rejected")
        self.assertIn(_MODULE.PARTIAL_EXPORT, exported["rejectedClaims"])
        marked = evaluate(payload(
            shareKind="unverified-partial",
            export_allowed=False,
            manifest=manifest(color_transfer="hlg"),
            labels=["HLG"],
            filename="partial.mov",
            interpretation=None,
            verificationSummaryPresent=True,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(marked["decision"], "rejected")
        self.assertIn(_MODULE.VERIFIED_PARTIAL, marked["rejectedClaims"])

    def test_share_kind_must_agree_with_transfer(self):
        result = evaluate(payload(
            shareKind="log-master",
            manifest=manifest(color_transfer="bt709"),
            labels=["Rec.709"],
            filename="wrong.mov",
            interpretation=None,
            metadataTexts=[],
            personalIdentifiers=[],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.KIND_TOKEN, result["rejectedClaims"])

    def test_publishing_private_paths_is_rejected(self):
        result = evaluate(payload(publishPrivatePaths=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("private-absolute-path", result["rejectedClaims"])
        self.assertNotIn(PRIVATE, blob(result))
        self.assertIn("p127-evidence", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(shareKind="raw"))
