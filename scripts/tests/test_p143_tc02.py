"""Tests for TC-P143-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc02",
        "repeat": "mixed-format",
        "looks": _GATE.fixture_looks(),
        "dropAmbiguous": False,
        "acquisitionMethods": ["35mm-color", "16mm-monochrome"],
        "titleMatchOnly": False,
        "assignedToEveryScene": False,
        "sceneVariants": [
            {"scene_id": "day-exterior", "method": "35mm-color", "uncertain": False},
            {"scene_id": "night-interior", "method": None, "uncertain": True},
        ],
    }
    base.update(overrides)
    return base


class TCP14302(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_scene_variants_and_distinct_releases_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["uncertainSceneIds"], ["night-interior"])
        self.assertEqual(len(record["acquisitionMethods"]), 2)
        self.assertEqual(
            result["preservedResults"][1]["acceptedKeys"],
            ["reference-film|digital-sdr|", "reference-film|theatrical-35mm|"],
        )
        self.assertEqual(_MODULE.CASE["name"], "Whole-film overgeneralization")

    def test_title_match_alone_is_rejected(self):
        result = evaluate(payload(titleMatchOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p143-tc02", result["preservedResults"])

    def test_assigning_one_method_to_every_scene_is_rejected(self):
        result = evaluate(payload(
            assignedToEveryScene=True,
            sceneVariants=[
                {"scene_id": "day-exterior", "method": "35mm-color", "uncertain": False},
                {"scene_id": "night-interior", "method": "35mm-color", "uncertain": False},
            ],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OVERGENERALIZED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc02-monochrome"
        result = evaluate(payload(evidenceId=evidence, repeat="monochrome"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(acquisitionMethods=[]))
