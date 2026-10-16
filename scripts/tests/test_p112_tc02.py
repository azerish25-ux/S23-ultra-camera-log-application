"""Tests for TC-P112-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def pixels(fill="current"):
    historical = 1.0
    current = 5.0
    if fill == "current":
        filled = current
    elif fill == "old":
        filled = historical
    else:
        filled = 9.0
    return [
        {
            "newly_visible": False,
            "historical_depth": historical,
            "current_depth": historical,
            "filled_depth": historical,
            "uncertainty": 0.05,
        },
        {
            "newly_visible": True,
            "historical_depth": historical,
            "current_depth": current,
            "filled_depth": filled,
            "uncertainty": 0.4,
        },
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p112-tc02",
        "repeat": "hair",
        "pixels": pixels("current"),
    }
    base.update(overrides)
    return base


class TCP11202(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_current_depth_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("uncertainty=0.4" in item for item in result["preservedResults"]))

    def test_old_depth_fill_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(pixels=pixels("old")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filled-newly-visible-pixels-with-old-depth", result["rejectedClaims"])

    def test_second_evidence_id_is_preserved(self):
        evidence = "p112-tc02-hands"
        result = evaluate(payload(evidenceId=evidence, repeat="hands"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        bad = pixels("current")
        bad[1]["uncertainty"] = -0.1
        with self.assertRaises(ValueError):
            evaluate(payload(pixels=bad))
