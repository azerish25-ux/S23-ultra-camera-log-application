"""Tests for TC-P109-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "translation",
        "shiftSamples": 2,
        "historyMode": "warped",
        "previousDepth": [0.2, 0.4, 0.6, 0.8],
        "currentDepth": [0.8, 0.2, 0.4, 0.6],
    }
    base.update(overrides)
    return base


class TCP10901(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-01")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_warped_history_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("history warped by 2 samples", " ".join(result["reasons"]))

    def test_negative_stationary_average_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(historyMode="stationary-average", shiftSamples=3))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stationary-pixel-average-depth-trails", result["rejectedClaims"])

    def test_mutant_stationary_average_is_rejected(self):
        result = evaluate(payload(historyMode="stationary-average", shiftSamples=-2, repeat="rotation"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stationary-pixel-average-depth-trails", result["rejectedClaims"])

    def test_rejected_history_and_second_repeat_preserve_evidence(self):
        evidence = "p109-camera-motion"
        result = evaluate(payload(evidenceId=evidence, repeat="camera motion", historyMode="rejected"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
