"""Tests for TC-P143-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc05",
        "repeat": "promotional-image",
        "looks": _GATE.fixture_looks(),
        "dropAmbiguous": False,
        "assetKind": "still",
        "publiclyAccessible": True,
        "redistributionPermission": "unknown",
        "citationRetained": True,
        "bytesInReleaseBundle": False,
        "treatsPublicAsLicence": False,
    }
    base.update(overrides)
    return base


class TCP14305(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_citation_without_bytes_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertTrue(record["citationRetained"])
        self.assertFalse(record["bytesInReleaseBundle"])
        self.assertTrue(record["publiclyAccessible"])
        self.assertEqual(len(result["preservedResults"][1]["distinctReleaseIds"]["reference-film"]), 2)

    def test_public_visibility_is_not_a_licence(self):
        result = evaluate(payload(treatsPublicAsLicence=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertTrue(result["preservedResults"][2]["citationRetained"])

    def test_unapproved_bytes_are_rejected(self):
        result = evaluate(payload(assetKind="commercial-lut", bytesInReleaseBundle=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNAPPROVED_BYTES, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc05-weights"
        result = evaluate(payload(evidenceId=evidence, repeat="research-weights", assetKind="research-weights"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(redistributionPermission="maybe"))
