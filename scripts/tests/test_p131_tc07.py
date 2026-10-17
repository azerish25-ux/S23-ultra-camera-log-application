"""Tests for TC-P131-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def side(**overrides):
    value = {"scale": 1, "transfer": "bt709", "enhanced": False, "time": 0}
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc07",
        "repeat": "source-versus-result",
        "committed": _GATE.make_control(),
        "proposed": _GATE.held_proposal(),
        "left": side(),
        "right": side(),
        "mismatchDisclosed": False,
        "preferenceJudgment": False,
    }
    base.update(overrides)
    return base


class TCP13107(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_aligned_comparison_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][2]["mismatch"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "auto-enhanced-comparison-side")

    def test_automatic_enhancement_is_rejected(self):
        result = evaluate(payload(left=side(enhanced=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(result["preservedResults"][1]["source_configuration"], _GATE.FIXTURE_SOURCE)

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc07-aspect"
        result = evaluate(payload(evidenceId=evidence, repeat="aspect"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(left=side(scale=0)))
