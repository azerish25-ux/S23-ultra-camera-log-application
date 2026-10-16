"""Tests for TC-P115-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p115_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p115_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
FRAMES = [[0.0, 0.0], [2.0, 4.0], [0.0, 0.0]]
WEIGHTS = [0.25, 0.5, 0.25]
WINDOW = [0, 2]


def independent_oracle(frames, weights):
    width = len(frames[0])
    return [sum(weights[k] * frames[k][i] for k in range(len(frames))) for i in range(width)]


def payload(**overrides):
    base = {
        "evidenceId": "p115-energy",
        "frames": FRAMES,
        "weights": WEIGHTS,
        "window": WINDOW,
        "oracle": [1.0, 2.0],
        "domain": "linear",
        "repeat": "constant-velocity",
    }
    base.update(overrides)
    return base


class TCP11503(unittest.TestCase):
    def assert_contract(self, result, evidence="p115-energy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P115-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Temporal integration energy")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Averaging display-encoded frames or unnormalized temporal weights must fail.",
        )
        self.assertIn("partial exposure", _MODULE.REPEAT)

    def test_numeric_example_matches_independent_oracle(self):
        oracle = independent_oracle(FRAMES, WEIGHTS)
        self.assertEqual(oracle, [1.0, 2.0])
        result = evaluate(payload(oracle=oracle))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn(WEIGHTS, result["preservedResults"])
        self.assertIn(WINDOW, result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [1.0, 2.0])
        for got, want in zip(result["preservedResults"][4], oracle):
            self.assertLessEqual(abs(got - want), 1e-9)

    def test_display_and_unnormalized_weights_are_rejected(self):
        displayed = evaluate(payload(domain="display"))
        self.assert_contract(displayed)
        self.assertEqual(displayed["decision"], "rejected")
        self.assertIn("display-encoded-average", displayed["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, displayed["reasons"])
        weights = [0.5, 0.5, 0.5]
        unnormalized = evaluate(payload(weights=weights, oracle=independent_oracle(FRAMES, weights)))
        self.assertEqual(unnormalized["decision"], "rejected")
        self.assertIn("unnormalized-temporal-weights", unnormalized["rejectedClaims"])
        self.assertIn(weights, unnormalized["preservedResults"])

    def test_acceleration_and_partial_boundary(self):
        frames = [[0.0, 0.0], [1.0, 2.0], [4.0, 8.0]]
        weights = [0.25, 0.25, 0.5]
        result = evaluate(
            payload(
                frames=frames,
                weights=weights,
                oracle=independent_oracle(frames, weights),
                repeat="acceleration",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][4], [2.25, 4.5])
        edge = [[1.0, 0.0], [3.0, 2.0], [9.0, 9.0], [8.0, 8.0]]
        edge_weights = [0.5, 0.5, 0.0, 0.0]
        edge_window = [0, 1]
        partial = evaluate(
            payload(
                frames=edge,
                weights=edge_weights,
                window=edge_window,
                oracle=independent_oracle(edge, edge_weights),
                repeat="partial-exposure-boundary",
            )
        )
        self.assertEqual(partial["decision"], "recorded")
        self.assertEqual(partial["preservedResults"][4], [2.0, 1.0])
        self.assertIn(edge_window, partial["preservedResults"])

    def test_outside_window_and_oracle_mismatch_are_rejected(self):
        frames = [[4.0, 0.0], [2.0, 4.0], [0.0, 8.0]]
        weights = [0.25, 0.5, 0.25]
        outside = evaluate(
            payload(
                frames=frames,
                weights=weights,
                window=[1, 2],
                oracle=independent_oracle(frames, weights),
                repeat="partial-exposure-boundary",
            )
        )
        self.assertEqual(outside["decision"], "rejected")
        self.assertIn("frame-outside-shutter-window", outside["rejectedClaims"])
        self.assertEqual(outside["preservedResults"][4], [2.0, 4.0])
        mismatch = evaluate(payload(oracle=[1.0, 2.0 + 1e-8]))
        self.assertEqual(mismatch["decision"], "rejected")
        self.assertIn("oracle-mismatch", mismatch["rejectedClaims"])

    def test_invalid_shape_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[[0.0, 0.0], [2.0]]))
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="handheld"))
