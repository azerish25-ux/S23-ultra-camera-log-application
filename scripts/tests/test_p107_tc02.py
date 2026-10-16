"""Tests for TC-P107-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def pixel(ident="px", **overrides):
    value = {
        "id": ident,
        "current_depth": 0.8,
        "historical_depth": None,
        "filled_with_old_depth": False,
        "uncertainty": 0.2,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "hands",
        "pixels": [pixel("a"), pixel("b", uncertainty=0.4)],
    }
    base.update(overrides)
    return base


class TCP10702(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_current_evidence_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("smear_fraction=0", result["preservedResults"])
        self.assertTrue(any("mean uncertainty" in item for item in result["reasons"]))

    def test_filling_every_new_pixel_with_old_depth_is_rejected(self):
        result = evaluate(
            payload(
                pixels=[
                    pixel("a", filled_with_old_depth=True, historical_depth=0.1),
                    pixel("b", filled_with_old_depth=True, historical_depth=0.1),
                ]
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("old-depth-fill", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("smear_fraction=1", result["preservedResults"])

    def test_one_smeared_pixel_is_rejected_and_evidence_remains(self):
        evidence = "p107-hair"
        result = evaluate(payload(evidenceId=evidence, pixels=[pixel("a", filled_with_old_depth=True), pixel("b")]))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("old-depth-fill", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(pixels=[pixel("a", uncertainty=-1.0)]))
        with self.assertRaises(ValueError):
            evaluate({})
