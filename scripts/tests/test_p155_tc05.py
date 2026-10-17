"""Tests for TC-P155-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def capture(**overrides):
    value = {
        "modeMenuExpanded": True,
        "validSensorSamples": 0,
        "decodedFidelity": "failed",
        "sustainedCadence": "not-checked",
        "thermal": "not-checked",
        "hypothesis": "failed",
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="sample receipt")
    base.update({"captureCheck": capture()})
    base.update(overrides)
    return base


class TCP15505(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_expanded_menu_without_samples_fails_the_hypothesis(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        preserved = result["preservedResults"][3]
        self.assertTrue(preserved["modeMenuExpanded"])
        self.assertEqual(preserved["validSensorSamples"], 0)
        self.assertEqual(preserved["hypothesis"], "failed")
        self.assertFalse(preserved["delivered"])
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")

    def test_visible_setting_is_not_useful_capture(self):
        result = evaluate(payload(captureCheck=capture(hypothesis="useful-capture")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][3]["validSensorSamples"], 0)

    def test_partial_checks_do_not_prove_useful_capture(self):
        result = evaluate(payload(captureCheck=capture(
            validSensorSamples=3,
            decodedFidelity="passed",
            sustainedCadence="failed",
            thermal="passed",
            hypothesis="useful-capture",
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][3]["delivered"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc05-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="thermal checks"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(captureCheck=capture(validSensorSamples=-1)))
        with self.assertRaises(ValueError):
            evaluate(payload(captureCheck=capture(hypothesis="qualified")))
