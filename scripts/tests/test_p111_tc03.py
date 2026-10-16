"""Tests for TC-P111-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat stationary backgrounds with changing foreground occupancy.",
        "normalization": "shared-scale",
        "stationaryIndex": 1,
        "frames": [[2.0, 4.0, 6.0], [1.0, 4.0, 10.0]],
    }
    base.update(overrides)
    return base


class TCP11103(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_shared_scale_keeps_the_stationary_depth(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("pump:0", result["preservedResults"])

    def test_independent_minmax_is_rejected(self):
        result = evaluate(payload(normalization="independent-minmax"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-minmax-normalization", result["rejectedClaims"])
        self.assertNotIn("pump:0", result["preservedResults"])
        self.assertTrue(any(item.startswith("pump:") and item != "pump:0" for item in result["preservedResults"]))

    def test_honest_reset_is_recorded(self):
        result = evaluate(payload(normalization="honest-reset", repeat="foreground occupancy"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("reset honestly" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[[2.0, 2.0], [1.0, 4.0]]))
