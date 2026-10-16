"""Tests for TC-P119-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p119_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p119_tc08.py",
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


def _guidance(**overrides):
    statement = {
        "text": "combined effects stay inside the measured limit",
        "limitId": "mode-24",
        "recommendsFps": None,
        "recommendsShutter": None,
        "observedMotionPx": 1.0,
        "claimsStableMotion": True,
        "promises": [],
    }
    statement.update(overrides)
    return [statement]


def payload(**overrides):
    base = {
        "evidenceId": "p119-combined",
        "stabilization": True,
        "virtualFocus": True,
        "motionIntegration": True,
        "filmFinishing": True,
        "combinedRun": True,
        "individualPassesOnly": False,
        "doubledEdges": False,
        "unstableMasks": False,
        "cadenceChanged": False,
        "cadenceExplained": False,
        "sharedGeometry": True,
        "frames": FRAMES,
        "weights": WEIGHTS,
        "window": WINDOW,
        "oracle": [1.0, 2.0],
        "repeat": "scene-cut",
        "selectedLimitId": "mode-24",
        "measuredLimits": [
            {
                "id": "mode-24",
                "fps": 24.0,
                "shutter_angle": 180.0,
                "max_stable_motion_px": 8.0,
                "mode_available": True,
            }
        ],
        "guidance": _guidance(),
    }
    base.update(overrides)
    return base


class TCP11908(unittest.TestCase):
    def assert_contract(self, result, evidence="p119-combined"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P119-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Combined temporal effects")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Independent success of each effect cannot replace the combined regression.",
        )
        self.assertIn("low-confidence motion", _MODULE.REPEAT)

    def test_combined_numeric_example_is_recorded(self):
        oracle = independent_oracle(FRAMES, WEIGHTS)
        self.assertEqual(oracle, [1.0, 2.0])
        result = evaluate(payload(oracle=oracle, repeat="chunk-resume"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(WEIGHTS, result["preservedResults"])
        self.assertIn(WINDOW, result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [1.0, 2.0])

    def test_individual_passes_do_not_replace_the_combined_run(self):
        result = evaluate(payload(individualPassesOnly=True, combinedRun=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-effects-replace-combined-regression", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][4], [1.0, 2.0])

    def test_doubled_edges_unstable_masks_and_cadence_are_rejected(self):
        result = evaluate(
            payload(
                doubledEdges=True,
                unstableMasks=True,
                sharedGeometry=False,
                cadenceChanged=True,
                cadenceExplained=False,
                repeat="low-confidence-motion",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("doubled-edges", result["rejectedClaims"])
        self.assertIn("unstable-masks", result["rejectedClaims"])
        self.assertIn("geometry-not-shared", result["rejectedClaims"])
        self.assertIn("unexplained-cadence-change", result["rejectedClaims"])

    def test_missing_effect_bad_oracle_and_ungrounded_guidance_fail(self):
        result = evaluate(payload(filmFinishing=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-combined-effect", result["rejectedClaims"])
        mismatch = evaluate(payload(oracle=[1.0, 3.0]))
        self.assertEqual(mismatch["decision"], "rejected")
        self.assertIn("oracle-mismatch", mismatch["rejectedClaims"])
        self.assertEqual(mismatch["preservedResults"][4], [1.0, 2.0])
        ungrounded = evaluate(payload(guidance=_guidance(limitId="", text="finish the clip like a film stock")))
        self.assertEqual(ungrounded["decision"], "rejected")
        self.assertIn("ungrounded-guidance", ungrounded["rejectedClaims"])
        self.assertIn("p119-combined", ungrounded["preservedResults"])
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[[0.0], [2.0, 4.0], [0.0, 0.0]]))
