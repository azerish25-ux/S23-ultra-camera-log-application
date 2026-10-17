"""Tests for TC-P144-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p144-tc07",
        "repeat": "faces",
        "declared_parameters": ["virtual-aperture", "grade"],
        "content_changes": [],
        "unrequested_synthesis": False,
        "generated_scene_as_footage": False,
        "recipe": _GATE.preferred_recipe(),
    }
    base.update(overrides)
    return base


class TCP14407(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_rendering_parameters_do_not_alter_content(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["content_changes"], [])
        self.assertFalse(record["generated_scene_as_footage"])
        self.assertFalse(record["report"]["identification"]["correct"])

    def test_generated_scene_is_not_footage(self):
        result = evaluate(payload(generated_scene_as_footage=True, unrequested_synthesis=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_FOOTAGE, result["rejectedClaims"])
        self.assertIn(_MODULE.SYNTHESIS, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_content_change_is_rejected(self):
        result = evaluate(payload(content_changes=["facial-geometry"], repeat="text"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ALTERED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc07-patterns"
        result = evaluate(payload(evidenceId=evidence, repeat="fine patterns"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_content_parameter_is_not_a_rendering_match(self):
        result = evaluate(payload(declared_parameters=["facial-geometry", "grade"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_RENDER, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(declared_parameters=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(content_changes=["wardrobe"]))
