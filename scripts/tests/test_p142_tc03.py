"""Tests for TC-P142-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p142-tc03",
        "repeat": "recipe-save",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "historical": _MODULE.default_historical(),
        "historicalAfter": _MODULE.default_historical(),
        "priorRecipe": _MODULE.default_prior(),
        "recipe": _MODULE.default_recipe(),
    }
    base.update(overrides)
    return base


class TCP14203(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_new_recipe_version_keeps_historical_facts(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        saved = result["preservedResults"][2]
        self.assertEqual(saved["version"], "recon-2")
        self.assertEqual(saved["historicalStock"], "unknown")
        self.assertTrue(saved["historicalUnchanged"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)

    def test_user_preference_cannot_replace_sourced_metadata(self):
        after = _MODULE.default_historical()
        after["stock"] = "5219"
        after["lens"] = "Cooke S4"
        result = evaluate(payload(historicalAfter=after))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["historicalStock"], "unknown")

    def test_grade_edit_without_a_new_version_is_rejected(self):
        recipe = _MODULE.default_recipe()
        recipe["version"] = "recon-1"
        result = evaluate(payload(recipe=recipe, repeat="rename"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NO_NEW_VERSION, result["rejectedClaims"])

    def test_recipe_grade_outside_bounds_is_rejected(self):
        recipe = _MODULE.default_recipe()
        recipe["exposure"] = 4.5
        result = evaluate(payload(recipe=recipe, repeat="share"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RECIPE_BOUNDS, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p142-tc03-update"
        result = evaluate(payload(evidenceId=evidence, repeat="catalogue-update"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        recipe = _MODULE.default_recipe()
        recipe["grain"] = -1
        with self.assertRaises(ValueError):
            evaluate(payload(recipe=recipe))
