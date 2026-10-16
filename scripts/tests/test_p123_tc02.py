"""Tests for TC-P123-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def recipe(**overrides):
    base = {
        "stock": "stock-a",
        "focus": "0.5",
        "grainSeed": "7",
        "outputRange": "full",
        "sourceInterpretation": "log",
    }
    base.update(overrides)
    return base


def payload(**overrides):
    base = {
        "evidenceId": "p123-recipe",
        "jobState": "running",
        "frozenRecipe": recipe(),
        "liveSliders": recipe(stock="stock-b"),
        "frameSources": ["frozen", "frozen"],
        "runningVersion": 2,
        "editVersion": 3,
        "repeat": "stock",
    }
    base.update(overrides)
    return base


class TCP12302(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-recipe"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Mutable recipe during export")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Reading live slider values for successive output frames must fail.",
        )
        self.assertIn("grain seed", _MODULE.REPEAT)

    def test_frozen_recipe_is_recorded_as_a_new_version(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["frozenRecipe"]["stock"], "stock-a")
        self.assertEqual(kept["liveSliders"]["stock"], "stock-b")
        self.assertEqual(result["preservedResults"][2], ["frozen", "frozen"])
        self.assertEqual(result["preservedResults"][3]["editVersion"], 3)

    def test_live_slider_frames_are_rejected(self):
        result = evaluate(payload(frameSources=["frozen", "live"], repeat="focus", liveSliders=recipe(focus="0.2")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("live-slider-read-for-output-frame", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["frozenRecipe"]["focus"], "0.5")
        self.assertEqual(result["preservedResults"][2], ["frozen", "live"])

    def test_edit_that_reuses_the_running_version_is_rejected(self):
        result = evaluate(payload(editVersion=2, repeat="grain-seed", liveSliders=recipe(grainSeed="9")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("running-job-not-versioned", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][3]["runningVersion"], 2)

    def test_unknown_state_and_bad_payload_raise(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(jobState="preparing"))
        with self.assertRaises(ValueError):
            evaluate(payload(liveSliders=recipe()))
