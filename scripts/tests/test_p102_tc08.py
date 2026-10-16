"""Tests for TC-P102-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "warm-operation",
        "standaloneLatencyMs": 12,
        "captureActive": True,
        "renderingActive": True,
        "encodingActive": True,
        "sustainedIntervalS": 30,
        "integratedSamples": [18, 22, 40, 28],
        "chosenOperation": "deferred",
        "claimedFrameRateGuarantee": False,
    }
    base.update(overrides)
    return base


class TCP10208(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_good_input_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("integrated-mean-ms:27.000", result["preservedResults"])

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(claimedFrameRateGuarantee=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("standalone-model-latency-become-full-camera", result["rejectedClaims"])
        self.assertIn("integrated-mean-ms:27.000", result["preservedResults"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc08-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="severe-thermal"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(integratedSamples=[12]))
