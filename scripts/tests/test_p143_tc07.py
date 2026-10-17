"""Tests for TC-P143-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
DECLARED = ["contrast", "red", "green", "blue"]


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc07",
        "repeat": "faces",
        "looks": _GATE.fixture_looks(),
        "dropAmbiguous": False,
        "suggestionApplied": True,
        "declaredParameters": list(DECLARED),
        "changedContent": [],
        "facialGeometryChanged": False,
        "sceneTextureReplaced": False,
        "contentSynthesis": False,
    }
    base.update(overrides)
    return base


class TCP14307(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_declared_parameters_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["declaredParameters"], DECLARED)
        self.assertEqual(len(result["preservedResults"][1]["acceptedKeys"]), 2)
        self.assertFalse(result["preservedResults"][2]["facialGeometryChanged"])

    def test_facial_geometry_change_is_rejected(self):
        result = evaluate(payload(facialGeometryChanged=True, changedContent=["faces"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NOT_CAMERA, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(len(result["preservedResults"][1]["entries"]), 2)

    def test_parameters_outside_the_declaration_are_rejected(self):
        result = evaluate(payload(declaredParameters=["contrast"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OUTSIDE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc07-text"
        result = evaluate(payload(evidenceId=evidence, repeat="text"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(changedContent=["faces", "costumes"]))
