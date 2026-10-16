"""Tests for TC-P127-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc06.py",
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
        "repeat": "local",
        "filename": "library.mov",
        "labels": ["Rec.709"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [],
        "interpretation": None,
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [],
        "grant": "valid",
        "filePresent": True,
        "thumbnailCached": True,
        "reportedAvailability": "available",
        "thumbnailUsedAsAccessProof": False,
        "historicalMetadataPreserved": True,
    }
    base.update(overrides)
    return base


class TCP12706(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_available_media_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("actualAvailability=available", result["preservedResults"])
        self.assertIn("historical metadata preserved", result["reasons"])

    def test_thumbnail_does_not_certify_revoked_media(self):
        result = evaluate(payload(
            grant="revoked",
            filePresent=False,
            thumbnailCached=True,
            reportedAvailability="unavailable",
            thumbnailUsedAsAccessProof=True,
            repeat="document-provider",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.AVAIL_TOKEN, result["rejectedClaims"])
        self.assertIn("actualAvailability=unavailable", result["preservedResults"])

    def test_revoked_media_can_keep_history_without_using_the_thumbnail(self):
        result = evaluate(payload(
            grant="missing",
            filePresent=False,
            thumbnailCached=True,
            reportedAvailability="unavailable",
            repeat="recovered",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("cached thumbnail kept as a preview, not as accessible media", result["reasons"])

    def test_misreported_availability_and_dropped_history_are_rejected(self):
        result = evaluate(payload(
            grant="revoked",
            filePresent=False,
            reportedAvailability="available",
            historicalMetadataPreserved=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.AVAIL_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.HISTORY_TOKEN, result["rejectedClaims"])
        self.assertIn("p127-evidence", result["preservedResults"])

    def test_display_relabel_is_rejected(self):
        result = evaluate(payload(labels=["Log"], filename="thumb_Log.mov"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-transfer-relabelled-as-log", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(grant="expired"))
