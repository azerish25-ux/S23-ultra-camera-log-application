"""Tests for TC-P123-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p123-access",
        "sourceGrant": "revoked",
        "filePresent": False,
        "thumbnailPresent": True,
        "thumbnailCertifiesAccess": False,
        "displayedAvailability": "unavailable",
        "historicalMetadata": "clip-history",
        "repeat": "local-file",
    }
    base.update(overrides)
    return base


class TCP12306(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-access"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Missing or revoked media access")
        self.assertEqual(_MODULE.NEGATIVE, "Thumbnail presence must not certify a valid source or output.")
        self.assertIn("document-provider", _MODULE.REPEAT)

    def test_revoked_source_keeps_history_and_does_not_trust_the_thumbnail(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1], "clip-history")
        self.assertFalse(result["preservedResults"][2]["actualAvailable"])
        self.assertTrue(result["preservedResults"][2]["thumbnailPresent"])
        self.assertEqual(result["preservedResults"][2]["displayedAvailability"], "unavailable")

    def test_thumbnail_does_not_certify_access(self):
        result = evaluate(
            payload(
                thumbnailCertifiesAccess=True,
                displayedAvailability="available",
                repeat="document-provider",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("thumbnail-certifies-source-or-output", result["rejectedClaims"])
        self.assertIn("availability-does-not-match-source", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1], "clip-history")
        self.assertFalse(result["preservedResults"][2]["actualAvailable"])

    def test_present_source_can_be_recorded(self):
        result = evaluate(
            payload(
                evidenceId="p123-present",
                sourceGrant="present",
                filePresent=True,
                displayedAvailability="available",
                repeat="recovered-private",
            )
        )
        self.assert_contract(result, "p123-present")
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["actualAvailable"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(historicalMetadata=""))
        with self.assertRaises(ValueError):
            evaluate(payload(sourceGrant="missing"))
