"""Tests for TC-P137-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def variant(scene, acquisition, stock, mode, source="src-northwater-stock"):
    return {
        "sceneFamily": scene,
        "acquisition": acquisition,
        "stock": stock,
        "mode": mode,
        "state": "fact",
        "source_id": source,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p137-tc02",
        "repeat": "mixed formats",
        "variants": [
            variant("day-exterior", "35mm-4-perf", "Eastman 5293", "color"),
            variant("night-interior", "16mm", "Double-X", "monochrome", "src-night-stock"),
        ],
        "assignToEveryShot": False,
        "titleMatchOnly": False,
        "sceneUnknowns": ["lens"],
    }
    base.update(overrides)
    return base


class TCP13702(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_variants_and_scene_uncertainty_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertEqual(len(detail["variants"]), 2)
        self.assertEqual(detail["sceneUnknowns"][0]["state"], "unknown")
        self.assertIsNone(detail["sceneUnknowns"][0]["value"])
        self.assertEqual(detail["stateCounts"]["fact"], 2)
        self.assertEqual(detail["stateCounts"]["unknown"], 1)
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Whole-film overgeneralization")

    def test_title_match_does_not_establish_every_scene(self):
        result = evaluate(payload(titleMatchOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.TITLE_MATCH, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(len(result["preservedResults"][1]["variants"]), 2)
        self.assertEqual(result["preservedResults"][1]["sceneUnknowns"][0]["name"], "lens")

    def test_assigning_one_method_to_every_shot_is_rejected(self):
        result = evaluate(payload(assignToEveryShot=True, repeat="location-specific stock choices"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.TITLE_MATCH, result["rejectedClaims"])

    def test_title_source_alone_is_rejected(self):
        variants = payload()["variants"]
        variants[0]["source_id"] = "title-match"
        result = evaluate(payload(variants=variants))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.TITLE_MATCH, result["rejectedClaims"])

    def test_repeat_covers_color_monochrome_and_formats(self):
        for repeat in ("mixed color/monochrome", "mixed formats", "location-specific stock choices"):
            result = evaluate(payload(repeat=repeat))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded")
            modes = {item["mode"] for item in result["preservedResults"][1]["variants"]}
            self.assertEqual(modes, {"color", "monochrome"})

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(sceneUnknowns="lens"))
