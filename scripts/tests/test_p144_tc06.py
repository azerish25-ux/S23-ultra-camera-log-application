"""Tests for TC-P144-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p144-tc06",
        "repeat": "theatrical",
        "editions": [
            {"edition_id": "theatrical", "appearance": "print-contrast"},
            {"edition_id": "digital", "appearance": "video-contrast"},
        ],
        "separate_targets": True,
        "uncertainty_explicit": True,
        "averaged_into_historical_fact": False,
        "recipe": _GATE.preferred_recipe(),
    }
    base.update(overrides)
    return base


class TCP14406(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_conflicting_editions_stay_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertTrue(record["inconsistent"])
        self.assertTrue(record["separate_targets"])
        self.assertFalse(record["report"]["historical_accuracy_claimed"])
        self.assertFalse(record["report"]["identification"]["correct"])

    def test_averaging_inconsistent_editions_is_rejected(self):
        result = evaluate(payload(averaged_into_historical_fact=True, repeat="HDR"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.AVERAGED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p144-tc06", result["preservedResults"])

    def test_one_definitive_look_is_rejected(self):
        result = evaluate(payload(separate_targets=False, uncertainty_explicit=False, repeat="unidentified"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INVENTED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc06-digital"
        result = evaluate(payload(evidenceId=evidence, repeat="digital"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(editions=[{"edition_id": "theatrical", "appearance": "print-contrast"}]))
