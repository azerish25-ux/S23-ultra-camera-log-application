"""Tests for TC-P160-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="sample receipt")
    base.update({
        "metadataChanged": True,
        "modeMenuExpanded": True,
        "validNewSensorOutput": False,
        "acquisitionHypothesis": "failed",
        "claimsUsefulCapture": False,
    })
    base.update(overrides)
    return base


class TCP16005(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_hypothesis_without_sensor_output_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["acquisitionHypothesis"], "failed")
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "visible-setting-proves-useful-capture")

    def test_visible_setting_is_not_useful_capture(self):
        result = evaluate(payload(claimsUsefulCapture=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.HYPOTHESIS_NOT_FAILED, result["rejectedClaims"])

    def test_accepting_the_hypothesis_without_output_is_rejected(self):
        result = evaluate(payload(acquisitionHypothesis="accepted"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HYPOTHESIS_NOT_FAILED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_valid_sensor_output_can_be_recorded(self):
        result = evaluate(payload(
            validNewSensorOutput=True,
            acquisitionHypothesis="accepted",
            claimsUsefulCapture=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc05-cadence"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained cadence"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(acquisitionHypothesis="maybe"))
