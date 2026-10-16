"""Tests for TC-P121-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-access",
        "repeat": "local-file",
        "sourceGrant": "valid",
        "thumbnailPresent": True,
        "treatedAsAccessible": True,
        "historicalMetadata": {"duration": "2s", "transfer": "bt709"},
    }
    base.update(overrides)
    return base


class TCP12106(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-access"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Missing or revoked media access")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Revoke the source grant or remove a file while the library still has a cached thumbnail.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Show actual availability and preserve historical metadata without treating the thumbnail as accessible media.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Thumbnail presence must not certify a valid source or output.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat local files, document-provider grants, and recovered private media.",
        )

    def test_valid_grant_is_available(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["availability"], "available")
        self.assertFalse(kept["thumbnailCertifiesSource"])
        self.assertEqual(kept["historicalMetadata"]["transfer"], "bt709")

    def test_thumbnail_does_not_certify_a_revoked_source(self):
        result = evaluate(
            payload(
                repeat="document-provider",
                sourceGrant="revoked",
                treatedAsAccessible=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THUMB_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["historicalMetadata"]["duration"], "2s")
        self.assertFalse(result["preservedResults"][1]["thumbnailCertifiesSource"])

    def test_revoked_media_stays_unavailable_with_metadata(self):
        result = evaluate(
            payload(
                evidenceId="p121-removed",
                repeat="recovered-private",
                sourceGrant="removed",
                thumbnailPresent=True,
                treatedAsAccessible=False,
            )
        )
        self.assert_contract(result, "p121-removed")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["availability"], "removed")
        self.assertEqual(result["preservedResults"][1]["historicalMetadata"]["transfer"], "bt709")
        hidden = evaluate(payload(sourceGrant="removed", thumbnailPresent=False, treatedAsAccessible=True))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("unavailable-source-treated-as-accessible", hidden["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceGrant="missing"))
        with self.assertRaises(ValueError):
            evaluate(payload(historicalMetadata={}))
