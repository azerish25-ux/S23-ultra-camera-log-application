"""Tests for TC-P133-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p133-tc02",
        "repeat": "preset",
        "controls": _GATE.fixture_controls(),
        "focusOrder": _GATE.fixture_focus_order(),
        "sourceMode": _GATE.FIXTURE_SOURCE_MODE,
        "sourceEvidenceStatus": "labelled-source-mode",
        "recipeLabel": _GATE.FIXTURE_RECIPE_LABEL,
        "recipeEvidenceStatus": "simulated",
        "displayedSourceLabel": _GATE.FIXTURE_SOURCE_MODE,
        "displayedRecipeLabel": _GATE.FIXTURE_RECIPE_LABEL,
    }
    base.update(overrides)
    return base


class TCP13302(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_source_and_simulated_recipe_stay_independent(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["recipeSeparate"])
        self.assertEqual(result["preservedResults"][2]["displayedSourceLabel"], "1080p SDR")
        self.assertEqual(result["preservedResults"][2]["recipeEvidenceStatus"], "simulated")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "renamed-source-mode-after-virtual-format")

    def test_renaming_the_source_after_the_virtual_format_is_rejected(self):
        result = evaluate(payload(displayedSourceLabel="IMAX 70mm", repeat="saved recipe"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["captureIds"], ["record", "stop", "source-status"])
        self.assertIn("p133-tc02", result["preservedResults"])

    def test_source_control_state_cannot_adopt_the_recipe_name(self):
        controls = _GATE.replace_control(
            _GATE.fixture_controls(), "source-status", state_description="IMAX 70mm"
        )
        result = evaluate(payload(controls=controls, repeat="export"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["sourceState"], "IMAX 70mm")

    def test_large_format_recipe_must_stay_simulated(self):
        result = evaluate(payload(recipeEvidenceStatus="qualified"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LARGE_FORMAT_UNLABELLED, result["rejectedClaims"])
        self.assertIn(_MODULE.LOOK_EVIDENCE_QUALIFIED, result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceMode=""))
