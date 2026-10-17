"""Tests for TC-P139-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p139-tc07",
        "repeat": "faces",
        "suggestion": {"virtualAperture": 4, "printContrast": 1.4},
    }
    base.update(_MODULE._CORE.bundle_for())
    base.update(overrides)
    return base


class TCP13907(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_declared_rendering_parameters_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("suggestionKeys=printContrast,virtualAperture", result["preservedResults"])

    def test_content_fields_are_rejected(self):
        cases = {
            "faces": "facialGeometry",
            "text": "renderedText",
            "fine-patterns": "finePattern",
            "moving-objects": "movingObjects",
        }
        for repeat, field in cases.items():
            suggestion = {"virtualAperture": 4, "printContrast": 1.4, field: "altered"}
            result = evaluate(payload(repeat=repeat, suggestion=suggestion))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "rejected", repeat)
            self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
            self.assertIn(_MODULE.SYNTHESIS, result["rejectedClaims"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertIn("p139-tc07", result["preservedResults"])

    def test_scene_texture_is_rejected(self):
        result = evaluate(
            payload(
                repeat="faces",
                suggestion={"grade": "neutral", "sceneTexture": "replaced"},
                evidenceId="p139-tc07-texture",
            )
        )
        self.assert_contract(result, "p139-tc07-texture")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sceneTexture", " ".join(result["reasons"]))

    def test_mutated_facts_are_rejected(self):
        result = evaluate(payload(mutated_facts=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(suggestion={}))
