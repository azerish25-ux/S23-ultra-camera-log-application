"""Tests for TC-P144-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p144-tc05",
        "repeat": "promotional images",
        "asset_kind": "still",
        "publicly_visible": True,
        "redistribution_known": False,
        "citation_retained": True,
        "bytes_in_release_bundle": False,
        "visibility_treated_as_licence": False,
        "recipe": _GATE.preferred_recipe(),
    }
    base.update(overrides)
    return base


class TCP14405(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_citation_stays_and_bytes_stay_out(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertTrue(record["citation_retained"])
        self.assertFalse(record["bytes_in_release_bundle"])
        self.assertTrue(record["publicly_visible"])
        self.assertFalse(record["report"]["identification"]["correct"])

    def test_visibility_is_not_a_licence(self):
        result = evaluate(payload(visibility_treated_as_licence=True, asset_kind="lut"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.VISIBILITY, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_unapproved_bytes_are_rejected(self):
        result = evaluate(payload(bytes_in_release_bundle=True, asset_kind="research-model-weights"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLICENSED_BYTES, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc05-profile"
        result = evaluate(payload(evidenceId=evidence, repeat="commercial LUTs", asset_kind="profile"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(asset_kind="soundtrack"))
