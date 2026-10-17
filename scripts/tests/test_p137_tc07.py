"""Tests for TC-P137-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p137-tc07",
        "repeat": "grade",
        "footageId": "take-northwater-1",
        "outputId": "take-northwater-1",
        "parameters": {"grade": "warm", "grain": "fine"},
        "alters": [],
    }
    base.update(overrides)
    return base


class TCP13707(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_declared_parameters_keep_the_footage(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertEqual(detail["preservedFootage"], "take-northwater-1")
        self.assertEqual(detail["parameters"]["grade"], "warm")
        self.assertEqual(detail["stateCounts"]["fact"], 1)
        self.assertEqual(detail["stateCounts"]["reconstruction"], 2)
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Parameter matching alters content")

    def test_facial_geometry_and_texture_are_rejected(self):
        for alter in ("faces", "facial_geometry", "scene_texture", "text", "fine_patterns", "moving_objects"):
            result = evaluate(payload(alters=[alter], repeat=alter))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "rejected", alter)
            self.assertIn(_GATE.CONTENT_SYNTHESIS, result["rejectedClaims"])
            self.assertIn(_GATE.GENERATED_SCENE, result["rejectedClaims"])
            self.assertIn(_MODULE.CASE["negative"], result["reasons"])
            self.assertEqual(result["preservedResults"][1]["preservedFootage"], "take-northwater-1")

    def test_a_different_output_is_not_camera_footage(self):
        result = evaluate(payload(outputId="generated-scene-9"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.GENERATED_SCENE, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["preservedFootage"], "take-northwater-1")
        self.assertNotEqual(result["preservedResults"][1]["preservedFootage"], "generated-scene-9")

    def test_undeclared_content_parameter_is_rejected(self):
        result = evaluate(payload(parameters={"facial_geometry": "slim"}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.CONTENT_SYNTHESIS, result["rejectedClaims"])
        self.assertIn(_GATE.GENERATED_SCENE, result["rejectedClaims"])
        self.assertNotIn("facial_geometry", result["preservedResults"][1]["parameters"])
        self.assertEqual(result["preservedResults"][1]["stateCounts"]["reconstruction"], 0)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(footageId=""))
