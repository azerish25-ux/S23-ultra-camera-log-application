"""Host checks for P115. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p115_build_a_temporal_integration_reference",
    Path(__file__).resolve().parents[1] / "gates" / "p115_build_a_temporal_integration_reference.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
TOLERANCE = _MODULE.TOLERANCE

_ROOT = Path(__file__).resolve().parents[2]
_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
_FRAMES = [[0.0, 0.0], [2.0, 4.0], [0.0, 0.0]]
_WEIGHTS = [0.25, 0.5, 0.25]
_WINDOW = [0, 2]


def independent_oracle(frames, weights):
    """Same weighted sum as the gate, written here so the oracle is not the gate."""
    width = len(frames[0])
    return [
        sum(weights[k] * frames[k][i] for k in range(len(frames)))
        for i in range(width)
    ]


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P115",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p115-disk-trail",
        "claim": "synthetic-host-fixture",
        "frames": _FRAMES,
        "weights": _WEIGHTS,
        "window": _WINDOW,
        "oracle": [1.0, 2.0],
        "domain": "linear",
        "applyMutant": False,
    }
    value.update(overrides)
    return value


class P115Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P115")
        self.assertEqual(_MODULE.TITLE, "Build a temporal integration reference")
        self.assertEqual(
            _MODULE.GOAL,
            "Create a controlled motion-blur oracle using known motion and synthetic intermediate samples.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A bright disk moving at constant velocity across a dark background with known subframe positions.",
        )
        self.assertEqual(
            _MODULE.DELIVERABLE,
            "Temporal integration reference and analytic motion fixtures",
        )
        self.assertIn("normalized weights", _MODULE.METHOD)
        self.assertEqual(_MODULE.TOLERANCE, 1e-9)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P114",))

    def test_numeric_example_is_recorded_as_one_two(self):
        oracle = independent_oracle(_FRAMES, _WEIGHTS)
        self.assertEqual(oracle, [1.0, 2.0])
        result = assess(document(oracle=oracle))
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p115-disk-trail", result["preservedResults"])
        self.assertIn(_WEIGHTS, result["preservedResults"])
        self.assertIn(_WINDOW, result["preservedResults"])
        self.assertIn([1.0, 2.0], result["preservedResults"])
        sample = result["preservedResults"][4]
        for got, want in zip(sample, oracle):
            self.assertLessEqual(abs(got - want), TOLERANCE)
        self.assertEqual(sample, [1.0, 2.0])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertAlmostEqual(sum(sample), 3.0, delta=TOLERANCE)

    def test_fixture_file_matches_the_numeric_example(self):
        payload = json.loads(
            (_ROOT / "docs" / "P115_BUILD_A_TEMPORAL_INTEGRATION_REFERENCE.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][4], [1.0, 2.0])
        self.assertEqual(result["preservedResults"][2], [0.25, 0.5, 0.25])
        self.assertEqual(result["preservedResults"][3], [0, 2])
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P115-handoff.json").read_text())
        self.assertEqual(handoff["nextPhase"], "P116")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertIn("physical S23 capture", handoff["unverified"])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p115-disk-trail", result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [1.0, 2.0])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_display_average_is_rejected(self):
        result = assess(document(domain="display"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-encoded-average", result["rejectedClaims"])
        self.assertIn(_WEIGHTS, result["preservedResults"])
        self.assertIn(_WINDOW, result["preservedResults"])

    def test_negative_weight_is_not_dropped(self):
        frames = [[1.0, 1.0], [2.0, 4.0], [0.0, 0.0]]
        weights = [-0.25, 0.75, 0.5]
        oracle = independent_oracle(frames, weights)
        self.assertEqual(oracle, [1.25, 2.75])
        result = assess(document(frames=frames, weights=weights, oracle=oracle))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("negative-weight", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2], weights)
        self.assertEqual(result["preservedResults"][4], [1.25, 2.75])
        self.assertNotEqual(result["preservedResults"][4], [1.5, 3.0])

    def test_unnormalized_weights_are_rejected(self):
        weights = [0.5, 0.5, 0.5]
        oracle = independent_oracle(_FRAMES, weights)
        result = assess(document(weights=weights, oracle=oracle))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unnormalized-temporal-weights", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2], weights)

    def test_frame_outside_window_stays_in_the_sum_and_is_rejected(self):
        frames = [[4.0, 0.0], [2.0, 4.0], [0.0, 8.0]]
        weights = [0.25, 0.5, 0.25]
        window = [1, 2]
        oracle = independent_oracle(frames, weights)
        self.assertEqual(oracle, [2.0, 4.0])
        result = assess(document(frames=frames, weights=weights, window=window, oracle=oracle))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("frame-outside-shutter-window", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][3], [1, 2])
        self.assertEqual(result["preservedResults"][4], [2.0, 4.0])
        self.assertNotEqual(result["preservedResults"][4], [1.0, 4.0])

    def test_zero_weight_outside_the_window_is_recorded(self):
        frames = [[4.0, 0.0], [2.0, 4.0], [0.0, 8.0]]
        weights = [0.0, 0.5, 0.5]
        window = [1, 2]
        oracle = independent_oracle(frames, weights)
        self.assertEqual(oracle, [1.0, 6.0])
        result = assess(document(frames=frames, weights=weights, window=window, oracle=oracle))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][4], oracle)
        self.assertIn(weights, result["preservedResults"])
        self.assertIn(window, result["preservedResults"])

    def test_oracle_mismatch_beyond_tolerance_is_rejected(self):
        result = assess(document(oracle=[1.0, 2.0 + 1e-8]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("oracle-mismatch", result["rejectedClaims"])
        self.assertIn("p115-disk-trail", result["preservedResults"])

    def test_mismatch_inside_tolerance_is_recorded(self):
        result = assess(document(oracle=[1.0, 2.0 + 5e-10]))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][4], [1.0, 2.0])

    def test_evaluate_uses_the_same_integral(self):
        result = evaluate(
            {
                "caseId": "P115",
                "evidenceId": "p115-evaluate",
                "claim": "synthetic-host-fixture",
                "frames": _FRAMES,
                "weights": _WEIGHTS,
                "window": _WINDOW,
                "oracle": independent_oracle(_FRAMES, _WEIGHTS),
                "domain": "linear",
                "applyMutant": False,
            }
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P115")
        self.assertEqual(result["preservedResults"][4], [1.0, 2.0])
        self.assertIn("p115-evaluate", result["preservedResults"])

    def test_invalid_shapes_raise(self):
        with self.assertRaises(ValueError):
            assess(document(frames=[[0.0, 0.0], [2.0]]))
        with self.assertRaises(ValueError):
            assess(document(weights=[0.25, 0.75]))
        with self.assertRaises(ValueError):
            assess(document(window=[2, 0]))
        with self.assertRaises(ValueError):
            assess(document(frames=[[0.0, float("nan")], [2.0, 4.0], [0.0, 0.0]]))
        with self.assertRaises(ValueError):
            assess(document(weights=[True, 0.0, 0.0]))
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate({})
