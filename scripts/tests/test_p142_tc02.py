"""Tests for TC-P142-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p142-tc02",
        "repeat": "mixed-formats",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "acquisitionMethods": ["35mm-color", "16mm-monochrome", "digital"],
        "shots": _MODULE.clean_shots(),
    }
    base.update(overrides)
    return base


class TCP14202(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_variants_and_scene_uncertainty_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        scenes = result["preservedResults"][2]["scenes"]
        self.assertEqual([item["method"] for item in scenes], ["35mm-color", "unknown", "16mm-monochrome"])
        self.assertEqual([item["color"] for item in scenes], [True, False, False])
        self.assertEqual(scenes[2]["stock"], "7222")
        self.assertIn("digital", result["preservedResults"][2]["acquisitionMethods"])

    def test_title_match_assigned_to_every_shot_is_rejected(self):
        shots = _MODULE.clean_shots()
        for shot in shots:
            shot["evidence"] = "title"
            shot["method"] = "35mm-color"
        result = evaluate(payload(shots=shots))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_uncertain_scene_cannot_be_filled(self):
        shots = _MODULE.clean_shots()
        shots[1]["method"] = "35mm-color"
        result = evaluate(payload(shots=shots, repeat="monochrome"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNCERTAINTY_ERASED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p142-tc02-stock"
        result = evaluate(payload(evidenceId=evidence, repeat="location-stock"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(acquisitionMethods=["only-one"]))
