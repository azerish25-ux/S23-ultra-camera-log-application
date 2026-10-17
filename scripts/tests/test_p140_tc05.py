"""Tests for TC-P140-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p140-tc05",
        "repeat": "promotional images",
        "assetId": "still-01",
        "assetKind": "still",
        "publiclyAccessible": True,
        "redistributionLicence": "unknown",
        "citation": "Archive still plate 14",
        "citationRetained": True,
        "bytesInReleaseBundle": False,
    }
    base.update(overrides)
    return base


class TCP14005(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_public_unknown_licence_keeps_citation_and_excludes_bytes(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["citation"], "Archive still plate 14")
        self.assertTrue(kept["bytesExcluded"])
        self.assertFalse(kept["bytesInReleaseBundle"])
        self.assertEqual(kept["searchIds"], ["still-01"])
        self.assertEqual(_MODULE.CASE["negative"], "Public visibility must not be treated as a redistribution licence.")

    def test_public_bytes_without_a_licence_are_rejected(self):
        result = evaluate(payload(bytesInReleaseBundle=True, assetKind="commercial-lut", repeat="commercial LUTs"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["citation"], "Archive still plate 14")
        self.assertFalse(result["preservedResults"][1]["bytesExcluded"])

    def test_dropped_citation_is_rejected(self):
        result = evaluate(payload(citationRetained=False, assetKind="research-model-weights", repeat="research model weights"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CITATION_DROPPED, result["rejectedClaims"])
        self.assertIsNone(result["preservedResults"][1]["citation"])
        self.assertEqual(result["preservedResults"][1]["searchIds"], [])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p140-tc05-profile"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="profile",
            assetKind="profile",
            redistributionLicence="granted",
            bytesInReleaseBundle=True,
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(redistributionLicence="public-domain-assumed"))
