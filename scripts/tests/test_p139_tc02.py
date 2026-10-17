"""Tests for TC-P139-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
METHODS = [
    {"scene": "day-exterior", "stock": "Kodak Vision3 250D", "format": "35mm", "color": "color"},
    {"scene": "night-interior", "stock": "Kodak Vision3 500T", "format": "35mm", "color": "color"},
    {"scene": "archive", "stock": "Eastman Double-X", "format": "16mm", "color": "monochrome"},
]
SUPPORTED = [
    {"scene": "day-exterior", "stock": "Kodak Vision3 250D", "evidence": "documented"},
    {"scene": "night-interior", "stock": "Kodak Vision3 500T", "evidence": "documented"},
    {"scene": "archive", "stock": "Eastman Double-X", "evidence": "documented"},
    {"scene": "untitled-insert", "stock": None, "evidence": "uncertain"},
]


def payload(**overrides):
    base = {
        "evidenceId": "p139-tc02",
        "repeat": "mixed-color-monochrome",
        "title": "Night Ferry",
        "methods": METHODS,
        "assignments": SUPPORTED,
        "titleMatchAlone": False,
    }
    base.update(_MODULE._CORE.bundle_for())
    base.update(overrides)
    return base


class TCP13902(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_supported_variants_and_scene_uncertainty_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("variant=archive:Eastman Double-X:16mm:monochrome", result["preservedResults"])
        self.assertIn("variant=day-exterior:Kodak Vision3 250D:35mm:color", result["preservedResults"])
        self.assertIn("scene=untitled-insert evidence=uncertain", result["preservedResults"])

    def test_title_match_alone_is_rejected(self):
        forced = [
            {"scene": "day-exterior", "stock": "Kodak Vision3 250D", "evidence": "documented"},
            {"scene": "night-interior", "stock": "Kodak Vision3 250D", "evidence": "documented"},
            {"scene": "archive", "stock": "Kodak Vision3 250D", "evidence": "documented"},
        ]
        result = evaluate(payload(assignments=forced, titleMatchAlone=True, repeat="location-specific-stock"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.COLLAPSED, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p139-tc02", result["preservedResults"])

    def test_mutated_facts_are_rejected(self):
        result = evaluate(payload(mutated_facts=True, repeat="mixed-formats"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p139-tc02-format"
        result = evaluate(payload(evidenceId=evidence, repeat="mixed-formats"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(titleMatchAlone="yes"))
