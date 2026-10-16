"""Tests for TC-P112-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
normalize_to_span = _MODULE.normalize_to_span

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frame(depths, low, high, reset=False):
    return {
        "depths": depths,
        "normalized": normalize_to_span(depths, low, high),
        "reset": reset,
    }


def payload(**overrides):
    locked = [
        frame([1.0, 2.0, 4.0], 1.0, 4.0, False),
        frame([1.0, 2.0, 8.0], 1.0, 4.0, False),
    ]
    base = {
        "evidenceId": "p112-tc03",
        "repeat": "stationary-background",
        "frames": locked,
    }
    base.update(overrides)
    return base


class TCP11203(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_locked_scale_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_independent_minmax_is_rejected_and_evidence_remains(self):
        frames = [
            frame([1.0, 2.0, 4.0], 1.0, 4.0, False),
            frame([1.0, 2.0, 8.0], 1.0, 8.0, False),
        ]
        result = evaluate(payload(frames=frames))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-minmax-normalization-per-frame", result["rejectedClaims"])

    def test_explicit_reset_is_recorded(self):
        frames = [
            frame([1.0, 2.0, 4.0], 1.0, 4.0, False),
            frame([1.0, 2.0, 8.0], 1.0, 8.0, True),
        ]
        result = evaluate(payload(frames=frames, evidenceId="p112-tc03-reset", repeat="occupancy"))
        self.assert_contract(result, "p112-tc03-reset")
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[
                frame([1.0, 1.0], 1.0, 4.0, False),
                frame([1.0, 2.0], 1.0, 4.0, False),
            ]))
