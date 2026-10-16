"""Tests for TC-P122-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc06",
        "repeat": "Repeat local files, document-provider grants, and recovered private media.",
        "sourceAvailable": False,
        "thumbnailPresent": True,
        "historicalMetadataPreserved": True,
        "treatedAsAccessibleMedia": False,
        "outputCertified": False,
        "versions": _MODULE.valid_versions(),
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12206(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_revoked_source_with_thumbnail_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sourceAvailable=False", result["preservedResults"])
        self.assertIn("thumbnailPresent=True", result["preservedResults"])

    def test_thumbnail_does_not_certify_access(self):
        result = evaluate(payload(treatedAsAccessibleMedia=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.UNAVAILABLE_TOKEN, result["rejectedClaims"])

    def test_thumbnail_does_not_certify_output(self):
        result = evaluate(payload(outputCertified=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_dropped_history_is_rejected(self):
        result = evaluate(payload(historicalMetadataPreserved=False, sourceAvailable=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.METADATA_TOKEN, result["rejectedClaims"])

    def test_recipe_hash_mismatch_is_rejected(self):
        versions = _MODULE.valid_versions()
        versions[1]["parent_id"] = None
        versions[1]["version_sha256"] = versions[0]["version_sha256"]
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-parent-version", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc06-grant"
        result = evaluate(payload(evidenceId=evidence, repeat="document-provider grants", sourceAvailable=True))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
