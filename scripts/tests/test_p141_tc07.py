"""Tests for TC-P141-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc07",
        "repeat": "faces",
        "assets": _GATE.fixture_assets(),
        "declaredParameters": ["exposure", "contrast"],
        "changes": ["contrast"],
        "presentedAsFootage": False,
    }
    base.update(overrides)
    return base


class TCP14107(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_declared_parameter_match_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["changes"], ["contrast"])
        self.assertEqual(record["contentChanges"], [])
        self.assertFalse(record["presentedAsFootage"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "generated-scene-not-preserved-footage")

    def test_generated_scene_presented_as_footage_is_rejected(self):
        result = evaluate(payload(changes=["facial-geometry", "scene-texture"], presentedAsFootage=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SYNTHESIS, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["contentChanges"], ["facial-geometry", "scene-texture"])

    def test_changes_outside_declared_parameters_are_rejected(self):
        result = evaluate(payload(changes=["saturation"], repeat="text"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OUTSIDE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.SYNTHESIS, result["rejectedClaims"])

    def test_content_tokens_repeat(self):
        for token, repeat in (
            ("faces", "faces"),
            ("text", "text"),
            ("fine-patterns", "fine patterns"),
            ("moving-objects", "moving objects"),
        ):
            result = evaluate(payload(changes=[token], declaredParameters=[token, "contrast"], repeat=repeat))
            self.assertEqual(result["decision"], "rejected", token)
            self.assertIn(_MODULE.SYNTHESIS, result["rejectedClaims"])

    def test_unlicensed_frame_is_rejected(self):
        frame = _GATE.make_asset(
            asset_id="grabbed-frame",
            kind="frame",
            licence=None,
            attribution=None,
            redistribute=False,
            bundled=True,
            citation="Frame citation",
        )
        result = evaluate(payload(assets=[frame]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNLICENSED_FRAME_BUNDLED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc07-patterns"
        result = evaluate(payload(evidenceId=evidence, repeat="fine patterns"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(declaredParameters=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(presentedAsFootage="no"))
