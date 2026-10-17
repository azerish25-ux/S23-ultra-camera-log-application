"""Tests for TC-P141-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def scenes():
    return [
        {"scene_id": "color", "acquisition": "color-35mm", "recipe": "color-35mm", "uncertain": False},
        {"scene_id": "mono", "acquisition": "monochrome", "recipe": "monochrome", "uncertain": False},
        {"scene_id": "location", "acquisition": "location-stock", "recipe": None, "uncertain": True},
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc02",
        "repeat": "mixed color/monochrome",
        "assets": _GATE.fixture_assets(),
        "titleMatchOnly": False,
        "scenes": scenes(),
    }
    base.update(overrides)
    return base


class TCP14102(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_variants_and_scene_uncertainty_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["uncertainSceneIds"], ["location"])
        self.assertIn("monochrome", record["acquisitions"])
        self.assertEqual(_MODULE.CASE["negative"], "A title match alone must not establish every scene\u2019s technical recipe.")
        self.assertIn("citation retained for " + _GATE.STILL_ID, result["reasons"])

    def test_title_match_alone_is_rejected(self):
        result = evaluate(payload(titleMatchOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["excludedAssetIds"], [_GATE.STILL_ID])

    def test_one_recipe_for_every_shot_is_rejected(self):
        flat = [
            {"scene_id": "a", "acquisition": "color-35mm", "recipe": "one-recipe", "uncertain": False},
            {"scene_id": "b", "acquisition": "monochrome", "recipe": "one-recipe", "uncertain": True},
        ]
        result = evaluate(payload(scenes=flat, repeat="mixed formats"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ONE_RECIPE, result["rejectedClaims"])

    def test_unlicensed_bundle_is_rejected(self):
        result = evaluate(payload(assets=[_GATE.make_asset(kind="frame", licence=None, bundled=True, attribution=None, redistribute=False)]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNLICENSED_FRAME_BUNDLED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc02-stock"
        result = evaluate(payload(evidenceId=evidence, repeat="location-specific stock choices"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(scenes=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(titleMatchOnly="yes"))
