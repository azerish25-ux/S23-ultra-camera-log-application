"""Tests for TC-P156-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="sample receipt")
    base.update({
        "modeMenuExpanded": True,
        "sensorFrames": 0,
        "validSensorOutput": False,
        "hypothesis": "not-delivered",
    })
    base.update(overrides)
    return base


class TCP15605(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_expanded_menu_without_frames_fails_the_hypothesis(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["delivered"])
        self.assertEqual(result["preservedResults"][3]["hypothesis"], "not-delivered")
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")

    def test_visible_setting_is_not_useful_capture(self):
        result = evaluate(payload(hypothesis="acquisition-delivered"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.HYPOTHESIS_NOT_FAILED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_valid_frames_can_record_delivery(self):
        result = evaluate(payload(
            sensorFrames=3,
            validSensorOutput=True,
            hypothesis="acquisition-delivered",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][3]["delivered"])

    def test_frames_without_valid_output_are_not_delivery(self):
        result = evaluate(payload(sensorFrames=4, validSensorOutput=False, hypothesis="acquisition-delivered"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertFalse(result["preservedResults"][3]["delivered"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc05-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="thermal checks"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sensorFrames=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(hypothesis="unlocked"))
