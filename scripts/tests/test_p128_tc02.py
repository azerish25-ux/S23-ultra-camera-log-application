"""Tests for TC-P128-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _long_form(**overrides):
    value = {
        "expected_frames": 6,
        "accounted_frames": [0, 1, 2, 3, 4, 5],
        "checkpoint_frames": [0, 2, 5],
        "audio_duration": 0.25,
        "video_duration": 0.25,
        "audio_absent": False,
        "spot_check_only": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p128-evidence",
        "repeat": "Repeat",
        "frozenRecipeId": "recipe-v1",
        "frameRecipeIds": ["recipe-v1"] * 6,
        "frozenSliderValue": 0.2,
        "liveSliderValue": 0.8,
        "frameBoundValues": [0.2] * 6,
        "editAfterStart": True,
        "subsequentRecipeId": "recipe-v2",
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12802(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frameAccount=", blob(result))
        self.assertTrue(result["reasons"])

    def test_live_slider_does_not_change_the_running_job(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frozenRecipeId=recipe-v1", result["preservedResults"])
        self.assertIn("subsequent edit created a new version; running job stays on the frozen recipe", result["reasons"])
        self.assertIn("frameAccount=6/6", blob(result))

    def test_live_slider_value_on_a_frame_is_rejected(self):
        bounds = [0.2] * 6
        bounds[3] = 0.8
        result = evaluate(payload(frameBoundValues=bounds))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("frame 3 read the live slider", result["reasons"])

    def test_frame_recipe_leaving_the_frozen_id_is_rejected(self):
        recipes = ["recipe-v1"] * 6
        recipes[1] = "live"
        result = evaluate(payload(frameRecipeIds=recipes))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_edit_that_reuses_the_frozen_id_is_rejected(self):
        result = evaluate(payload(subsequentRecipeId="recipe-v1"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTATION_TOKEN, result["rejectedClaims"])

    def test_duplicate_frame_is_rejected_inside_the_case(self):
        result = evaluate(payload(accounted_frames=[0, 1, 2, 2, 3, 4, 5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-grain"
        result = evaluate(payload(evidenceId=evidence, repeat="grain"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
