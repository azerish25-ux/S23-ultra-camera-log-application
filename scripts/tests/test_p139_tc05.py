"""Tests for TC-P139-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p139-tc05",
        "repeat": "promotional-images",
        "assetKind": "promotional-images",
        "publiclyAccessible": True,
        "redistributionLicence": "unknown",
        "citation": "production still, rights unknown",
        "includedInBundle": False,
        "byteCount": 1200,
    }
    base.update(_MODULE._CORE.bundle_for())
    base.update(overrides)
    return base


class TCP13905(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_unknown_licence_keeps_citation_and_drops_bytes(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("citation=production still, rights unknown", result["preservedResults"])
        self.assertIn("bytesExcluded=true", result["preservedResults"])

    def test_public_visibility_is_not_a_licence(self):
        result = evaluate(payload(includedInBundle=True, assetKind="commercial-luts", repeat="commercial-luts"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("citation=production still, rights unknown", result["preservedResults"])
        self.assertIn("bytesExcluded=false", result["preservedResults"])

    def test_private_unlicensed_bytes_are_rejected(self):
        result = evaluate(
            payload(
                publiclyAccessible=False,
                redistributionLicence="denied",
                includedInBundle=True,
                assetKind="research-model-weights",
                repeat="research-model-weights",
                evidenceId="p139-tc05-weights",
            )
        )
        self.assert_contract(result, "p139-tc05-weights")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLICENSED_BYTES, result["rejectedClaims"])

    def test_mutated_facts_are_rejected(self):
        result = evaluate(payload(mutated_facts=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, result["rejectedClaims"])
        self.assertIn("citation=production still, rights unknown", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(byteCount=-1))
