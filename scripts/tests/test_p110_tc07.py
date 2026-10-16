"""Tests for TC-P110-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def strip():
    return [
        {"depth": 0.0, "value": 0.75, "layer": "foreground"},
        {"depth": 0.5, "value": 1.0, "layer": "foreground"},
        {"depth": 2.0, "value": 0.25, "layer": "focus"},
        {"depth": 2.0, "value": 0.5, "layer": "focus"},
        {"depth": 5.0, "value": 1.0, "layer": "background"},
        {"depth": 4.0, "value": 0.0, "layer": "background"},
        {"depth": None, "value": -1.0, "layer": "unknown"},
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat perfect-depth",
        "focus": 2.0,
        "samples": strip(),
        "label": "depth-ordered",
    }
    base.update(overrides)
    return base


class TCP11007(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_depth_ordered_bokeh_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("focus:0.25:nw=0" in item for item in result["reasons"]))

    def test_uniform_background_without_coverage_is_rejected(self):
        result = evaluate(payload(label="uniform-background"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("uniform-background-blur-without-foreground-coverage", result["rejectedClaims"])
        self.assertIn("background-leak-through-focus", result["rejectedClaims"])

    def test_optical_bokeh_and_unknown_as_far_are_rejected(self):
        optical = evaluate(payload(label="optical_bokeh"))
        self.assertEqual(optical["decision"], "rejected")
        self.assertIn("optical_bokeh", optical["rejectedClaims"])
        self.assertIn("foreground-bleed", optical["rejectedClaims"])
        self.assertIn("p110-evidence", optical["preservedResults"])
        unknown = evaluate(payload(label="unknown-as-far"))
        self.assertEqual(unknown["decision"], "rejected")
        self.assertIn("unknown-treated-as-far", unknown["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(samples=[{"depth": None, "value": 1.0, "layer": "background"}]))
