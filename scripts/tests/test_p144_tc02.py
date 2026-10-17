"""Tests for TC-P144-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    methods = ["35mm-color", "16mm-monochrome"]
    base = {
        "evidenceId": "p144-tc02",
        "repeat": "mixed color/monochrome",
        "acquisition_methods": methods,
        "assign_one_to_every_shot": False,
        "title_match_only": False,
        "supported_variants": list(methods),
        "scene_uncertainty_preserved": True,
        "recipe": _GATE.preferred_recipe(),
    }
    base.update(overrides)
    return base


class TCP14402(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_variants_and_scene_uncertainty_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["supported_variants"], ["35mm-color", "16mm-monochrome"])
        self.assertTrue(record["scene_uncertainty_preserved"])
        self.assertFalse(record["report"]["identification"]["correct"])
        self.assertIn("\u2019", _MODULE.CASE["negative"])

    def test_title_match_alone_is_rejected(self):
        result = evaluate(payload(title_match_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TITLE_MATCH, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_one_method_for_every_shot_is_rejected(self):
        result = evaluate(payload(assign_one_to_every_shot=True, repeat="location-specific stock"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ASSIGN_ALL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc02-formats"
        result = evaluate(payload(evidenceId=evidence, repeat="mixed formats"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(acquisition_methods=["only-one"]))
