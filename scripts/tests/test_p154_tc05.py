"""Tests for TC-P154-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def checks(**overrides):
    value = {
        "sampleReceipt": False,
        "decodedFidelity": False,
        "sustainedCadence": False,
        "thermal": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="sample receipt")
    base.update({
        "modeMenuExpanded": True,
        "newSettingVisible": True,
        "validSensorOutput": False,
        "acquisitionHypothesis": "fail",
        "settingTreatedAsCaptureProof": False,
        "checks": checks(),
    })
    base.update(overrides)
    return base


class TCP15405(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_hypothesis_without_sensor_output_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["acquisitionHypothesis"], "fail")
        self.assertFalse(result["preservedResults"][3]["validSensorOutput"])
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "visible-setting-is-not-useful-capture")

    def test_visible_setting_is_not_proof_of_useful_capture(self):
        result = evaluate(payload(
            acquisitionHypothesis="pass",
            settingTreatedAsCaptureProof=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.HYPOTHESIS_NOT_FAILED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_passing_hypothesis_without_checks_is_rejected(self):
        result = evaluate(payload(
            validSensorOutput=True,
            acquisitionHypothesis="pass",
            checks=checks(sampleReceipt=True),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HYPOTHESIS_NOT_FAILED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_treating_the_setting_as_proof_is_rejected_even_if_the_hypothesis_fails(self):
        result = evaluate(payload(settingTreatedAsCaptureProof=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.HYPOTHESIS_NOT_FAILED, result["rejectedClaims"])

    def test_verified_notes_are_still_rejected(self):
        result = evaluate(payload(notesStatus="verified-on-user-phone"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.NOTES_NOT_UNVERIFIED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc05-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="thermal checks"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(acquisitionHypothesis="maybe"))
        with self.assertRaises(ValueError):
            evaluate(payload(checks={"sampleReceipt": False}))
