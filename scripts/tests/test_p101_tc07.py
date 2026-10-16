"""Tests for TC-P101-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p101_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p101-tc07",
        "repeat": "transparent surfaces",
        "scores": [0.33, 0.91],
        "label": "uncalibrated",
        "presentedAs": "uncalibrated-score",
        "renderingReliance": "reduced",
    }
    base.update(overrides)
    return base


class TCP10107(unittest.TestCase):
    def assert_contract(self, result, evidence="p101-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P101-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_uncalibrated_label_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("confidence labelled uncalibrated", " ".join(result["reasons"]))

    def test_calibrated_probability_claim_is_rejected(self):
        result = evaluate(payload(
            scores=[0.99],
            label="calibrated-probability",
            presentedAs="calibrated-probability",
            renderingReliance="full",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("arbitrary-confidence-score-presented-calibrated-probability", result["rejectedClaims"])
        self.assertIn("rendering-reliance-not-reduced", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p101-tc07-mirrors"
        result = evaluate(payload(evidenceId=evidence, repeat="mirrors"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(presentedAs="certain"))
