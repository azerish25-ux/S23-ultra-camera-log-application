"""Tests for TC-P137-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def asset(**overrides):
    value = {
        "kind": "still",
        "publiclyAccessible": True,
        "redistribution": "unknown",
        "citation": "src-still-credit",
        "bytesInBundle": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {"evidenceId": "p137-tc05", "repeat": "still", "asset": asset()}
    base.update(overrides)
    return base


class TCP13705(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unknown_permission_keeps_citation_and_drops_bytes(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertEqual(detail["citation"], "src-still-credit")
        self.assertFalse(detail["bytesInBundle"])
        self.assertTrue(detail["bundleExcluded"])
        self.assertEqual(detail["redistribution"], "unknown")
        self.assertEqual(detail["stateCounts"]["fact"], 1)
        self.assertEqual(detail["stateCounts"]["unknown"], 1)
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Publicly accessible but unlicensed asset")

    def test_unapproved_bytes_are_rejected(self):
        result = evaluate(payload(asset=asset(bytesInBundle=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNAPPROVED_BYTES, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["citation"], "src-still-credit")
        self.assertTrue(result["preservedResults"][1]["bytesInBundle"])

    def test_public_visibility_is_not_a_licence(self):
        result = evaluate(payload(asset=asset(redistribution="public-visibility", bytesInBundle=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PUBLIC_AS_LICENCE, result["rejectedClaims"])
        self.assertIn(_GATE.UNAPPROVED_BYTES, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["citation"], "src-still-credit")

    def test_a_real_licence_may_include_bytes(self):
        result = evaluate(payload(asset=asset(redistribution="licensed", bytesInBundle=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][1]["bytesInBundle"])
        self.assertEqual(result["preservedResults"][1]["stateCounts"]["fact"], 2)
        self.assertEqual(result["preservedResults"][1]["stateCounts"]["unknown"], 0)

    def test_repeat_kinds_keep_the_same_rule(self):
        for kind in ("promotional-image", "commercial-lut", "research-weights"):
            result = evaluate(payload(asset=asset(kind=kind), repeat=kind))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded", kind)
            self.assertEqual(result["preservedResults"][1]["kind"], kind)
            self.assertFalse(result["preservedResults"][1]["bytesInBundle"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(asset=asset(citation="  ")))
