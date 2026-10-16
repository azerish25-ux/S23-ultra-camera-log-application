"""Tests for TC-P125-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p125-access",
        "repeat": "local-file",
        "accessKind": "local-file",
        "grantState": "revoked",
        "thumbnailCached": True,
        "availability": "unavailable",
        "historicalMetadataPreserved": True,
        "thumbnailCertifiesMedia": False,
    }
    base.update(overrides)
    return base


class TCP12506(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-access"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Missing or revoked media access")
        self.assertEqual(_MODULE.NEGATIVE, "Thumbnail presence must not certify a valid source or output.")
        self.assertEqual(_MODULE.REPEAT, "Repeat local files, document-provider grants, and recovered private media.")

    def test_revoked_grant_with_thumbnail_is_unavailable(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        kept = result["preservedResults"][1]
        self.assertEqual(kept["availability"], "unavailable")
        self.assertTrue(kept["thumbnailCached"])
        self.assertTrue(kept["historicalMetadataPreserved"])
        self.assertFalse(kept["thumbnailCertifiesMedia"])

    def test_thumbnail_does_not_certify(self):
        result = evaluate(payload(thumbnailCertifiesMedia=True, availability="available"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THUMBNAIL_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.AVAILABILITY_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["grantState"], "revoked")

    def test_removed_file_keeps_metadata(self):
        result = evaluate(
            payload(
                evidenceId="p125-removed",
                repeat="recovered-private",
                accessKind="recovered-private",
                grantState="removed",
                historicalMetadataPreserved=False,
            )
        )
        self.assert_contract(result, "p125-removed")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.METADATA_TOKEN, result["rejectedClaims"])

    def test_valid_grant_is_available(self):
        result = evaluate(
            payload(
                evidenceId="p125-valid",
                repeat="document-provider",
                accessKind="document-provider",
                grantState="valid",
                availability="available",
                thumbnailCached=False,
            )
        )
        self.assert_contract(result, "p125-valid")
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(grantState="missing"))
