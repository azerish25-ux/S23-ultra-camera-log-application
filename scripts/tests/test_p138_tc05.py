"""Tests for TC-P138-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def asset(**overrides):
    value = {
        "kind": "still",
        "source_id": "still-citation-1",
        "citation": "Production still, redistribution unknown",
        "publiclyAccessible": True,
        "redistributionLicensed": None,
        "includeBytes": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc05",
        "repeat": "promotional images",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "asset": asset(),
    }
    base.update(overrides)
    return base


class TCP13805(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unknown_licence_keeps_the_citation_and_drops_bytes(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["citation"], "Production still, redistribution unknown")
        self.assertEqual(record["source_id"], "still-citation-1")
        self.assertFalse(record["bytesIncluded"])
        self.assertIsNone(record["redistributionLicensed"])
        self.assertTrue(record["publiclyAccessible"])

    def test_public_bytes_without_a_licence_are_rejected(self):
        result = evaluate(payload(asset=asset(includeBytes=True, kind="lut")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertFalse(result["preservedResults"][2]["bytesIncluded"])
        self.assertEqual(result["preservedResults"][2]["citation"], "Production still, redistribution unknown")

    def test_explicit_licence_may_include_bytes(self):
        evidence = "p138-tc05-weights"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="research model weights",
            asset=asset(
                kind="research-weights",
                redistributionLicensed=True,
                includeBytes=True,
                citation="Research weights, licence granted",
            ),
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["bytesIncluded"])

    def test_commercial_lut_without_permission_is_rejected(self):
        result = evaluate(payload(
            repeat="commercial LUTs",
            asset=asset(kind="commercial-lut", redistributionLicensed=False, includeBytes=True),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(asset=asset(kind="video")))
        with self.assertRaises(ValueError):
            evaluate(payload(asset=asset(citation="")))
