"""Tests for TC-P103-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p103_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p103-evidence",
        "repeat": "Repeat",
        "applyNegative": False,
        "applyMutant": False,
        "sourceWidth": 1080,
        "sourceHeight": 1920,
        "preparedWidth": 540,
        "preparedHeight": 960,
        "stretchRecorded": False,
        "channelOrder": "RGB",
        "expectedChannelOrder": "RGB",
        "cornersRestored": True,
    }
    base.update(overrides)
    return base


class TCP10302(unittest.TestCase):
    def assert_contract(self, result, evidence="p103-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P103-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(applyNegative=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-stretching-swapped-color-channels-fail", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="portrait"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-stretching-swapped-color-channels-fail", result["rejectedClaims"])

    def test_unrecorded_stretch_is_rejected(self):
        result = evaluate(payload(preparedWidth=960, preparedHeight=540, stretchRecorded=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-stretching-swapped-color-channels-fail", result["rejectedClaims"])

    def test_swapped_channels_are_rejected(self):
        result = evaluate(payload(channelOrder="BGR"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-stretching-swapped-color-channels-fail", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p103-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceWidth=0))
