"""Tests for TC-P140-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def scenes():
    return [
        {
            "sceneId": "scene-studio",
            "acquisition": "35mm photochemical",
            "monochrome": True,
            "format": "35mm",
            "stock": "Double-X",
            "location": "studio",
            "uncertain": False,
        },
        {
            "sceneId": "scene-desert",
            "acquisition": "65mm photochemical",
            "monochrome": False,
            "format": "large-format",
            "stock": "Vision3 250D",
            "location": "desert",
            "uncertain": True,
        },
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p140-tc02",
        "repeat": "mixed formats",
        "movieId": "night-hunter",
        "title": "Night Hunter",
        "scenes": scenes(),
        "assignOneMethodToEveryScene": False,
        "uncertaintyWiped": False,
    }
    base.update(overrides)
    return base


class TCP14002(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_variants_and_scene_uncertainty_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["acquisitions"], ["35mm photochemical", "65mm photochemical"])
        self.assertFalse(kept["singleRecipeAssigned"])
        self.assertIn("scene-desert", kept["titleIds"])
        self.assertEqual(kept["stockLookups"][0], ["scene-studio"])
        self.assertEqual(kept["stockLookups"][1], ["scene-desert"])
        self.assertTrue(kept["sceneRecipes"][1]["uncertain"])
        self.assertIn("scene\u2019s", _MODULE.CASE["negative"])

    def test_title_match_assigned_to_every_scene_is_rejected(self):
        result = evaluate(payload(assignOneMethodToEveryScene=True, repeat="mixed color/monochrome"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(len(result["preservedResults"][1]["sceneRecipes"]), 2)
        self.assertFalse(result["preservedResults"][1]["singleRecipeAssigned"])

    def test_wiped_uncertainty_is_rejected(self):
        result = evaluate(payload(uncertaintyWiped=True, repeat="location-specific stock"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WIPED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p140-tc02-stock"
        result = evaluate(payload(evidenceId=evidence, repeat="location-specific stock choices"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(scenes=scenes()[:1]))
