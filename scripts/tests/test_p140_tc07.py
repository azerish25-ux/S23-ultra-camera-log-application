"""Tests for TC-P140-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p140_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p140_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p140-tc07",
        "repeat": "faces",
        "contentClass": "faces",
        "declaredParameters": {"contrast": 1.1, "grain": 0.2},
        "altersFacialGeometry": False,
        "replacesSceneTexture": False,
        "generatedScene": False,
    }
    base.update(overrides)
    return base


class TCP14007(unittest.TestCase):
    def assert_contract(self, result, evidence="p140-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P140-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_declared_rendering_parameters_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["parameterKeys"], ["contrast", "grain"])
        self.assertEqual(kept["searchIds"], ["render-match-faces"])
        self.assertTrue(kept["preservedFootage"])

    def test_generated_scene_is_not_preserved_footage(self):
        result = evaluate(payload(generatedScene=True, altersFacialGeometry=True, repeat="text"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SYNTHESIS, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertFalse(result["preservedResults"][1]["preservedFootage"])

    def test_texture_replacement_parameter_is_rejected(self):
        result = evaluate(payload(
            contentClass="fine-patterns",
            repeat="fine patterns",
            replacesSceneTexture=True,
            declaredParameters={"contrast": 1.0, "texture": 1.0},
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_RESTRICTED, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["parameterKeys"], ["contrast"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p140-tc07-motion"
        result = evaluate(payload(evidenceId=evidence, repeat="moving objects", contentClass="moving-objects"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(contentClass="sky"))
