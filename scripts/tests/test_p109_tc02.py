"""Tests for TC-P109-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def pixel(valid, source, historical=0.2, current=0.8):
    return {
        "historicalValid": valid,
        "historicalDepth": historical,
        "currentDepth": current,
        "source": source,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "hair",
        "pixels": [pixel(False, "uncertain"), pixel(True, "history", 0.2, 0.2)],
    }
    base.update(overrides)
    return base


class TCP10902(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-02")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_uncertain_disocclusion_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_old_depth_fill_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(pixels=[pixel(False, "history"), pixel(False, "history", 0.4, 0.9)]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("disoccluded-filled-with-old-depth", result["rejectedClaims"])

    def test_mutant_old_depth_fill_is_rejected(self):
        result = evaluate(payload(repeat="hands", pixels=[pixel(False, "current"), pixel(False, "history")]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("disoccluded-filled-with-old-depth", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p109-thin-objects"
        result = evaluate(payload(evidenceId=evidence, repeat="thin objects", pixels=[pixel(False, "current")]))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
