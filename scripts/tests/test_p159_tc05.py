"""Tests for TC-P159-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p159_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p159_tc05.py",
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
        "samplesReceived": 0,
        "decodedFidelity": None,
        "sustainedCadence": False,
        "thermalChecked": False,
        "hypothesisAccepted": False,
    })
    base.update(overrides)
    return base


class TCP15905(unittest.TestCase):
    def assert_contract(self, result, evidence="p159-computational-optics"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P159-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_expanded_menu_without_acceptance_fails_the_hypothesis(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["samplesReceived"], 0)
        self.assertFalse(result["preservedResults"][3]["hypothesisAccepted"])
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")

    def test_visible_setting_is_not_useful_capture(self):
        result = evaluate(payload(hypothesisAccepted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.HYPOTHESIS_WITHOUT_OUTPUT, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_samples_without_fidelity_still_reject_acceptance(self):
        result = evaluate(payload(samplesReceived=4, hypothesisAccepted=True, modeMenuExpanded=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HYPOTHESIS_WITHOUT_OUTPUT, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_real_sensor_output_can_accept_the_hypothesis(self):
        result = evaluate(payload(
            samplesReceived=8,
            decodedFidelity=0.9,
            sustainedCadence=True,
            thermalChecked=True,
            hypothesisAccepted=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][3]["decodedFidelity"], 0.9)

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p159-tc05-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="thermal checks"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(samplesReceived=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(decodedFidelity=1.5))
