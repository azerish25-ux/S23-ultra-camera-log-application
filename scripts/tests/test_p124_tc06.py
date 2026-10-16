"""Tests for TC-P124-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "sourceGrant": "revoked",
        "filePresent": False,
        "thumbnailPresent": True,
        "availability": "unavailable",
        "historicalMetadataPreserved": True,
        "thumbnailTreatedAsMedia": False,
    }
    base.update(overrides)
    return base


class TCP12406(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_revoked_source_with_thumbnail_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("thumbnailPresent=true", result["preservedResults"])
        self.assertIn("availability=unavailable", result["preservedResults"])

    def test_thumbnail_must_not_certify_the_source(self):
        result = evaluate(payload(thumbnailTreatedAsMedia=True, availability="available"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THUMBNAIL, result["rejectedClaims"])
        self.assertIn(_MODULE.AVAILABILITY, result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_dropped_metadata_is_rejected(self):
        result = evaluate(payload(historicalMetadataPreserved=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.METADATA, result["rejectedClaims"])

    def test_valid_file_is_available(self):
        result = evaluate(payload(sourceGrant="valid", filePresent=True, availability="available",
                                  thumbnailPresent=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-provider"
        result = evaluate(payload(evidenceId=evidence, repeat="provider"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
