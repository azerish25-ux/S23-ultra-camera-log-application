"""Tests for TC-P158-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15805(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_expanded_menu_without_frames_fails_the_hypothesis(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["hypothesisFailed"], True)
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))

    def test_visible_setting_without_frames_is_rejected(self):
        result = evaluate(payload(hypothesisAccepted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_valid_frames_can_accept_the_hypothesis(self):
        result = evaluate(payload(
            sensorFramesValid=True,
            sensorFrameCount=3,
            hypothesisAccepted=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_sensor_derived_log_claim_is_rejected_inside_the_case(self):
        result = evaluate(payload(claimsSensorDerivedLog=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.SENSOR_DERIVED_LOG, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc05-cadence"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained-cadence"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(sensorFramesValid=True, sensorFrameCount=0))
        with self.assertRaises(ValueError):
            evaluate(payload(sensorFrameCount=-1))
