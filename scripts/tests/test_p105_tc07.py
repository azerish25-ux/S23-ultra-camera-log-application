"""Tests for TC-P105-07."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p105_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p105_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
STAMPS = [0, 40, 80, 120, 160, 200, 240, 280]
LUMA = [0.2, 0.22, 0.21, 0.23, 0.24, 0.22, 0.25, 0.23]


def payload(**overrides):
    base = {
        "evidenceId": "p105-tc07",
        "repeat": "perfect-depth",
        "nominalFramePeriodMs": 40,
        "frameTimestampsMs": list(STAMPS),
        "lumaMeans": list(LUMA),
        "hideGap": False,
        "useKeyframeAsBaseline": False,
        "keyframeScore": None,
        **{
        "blurMode": "layered",
        "foregroundCoverageModel": True
    },
    }
    base.update(overrides)
    return base


class TCP10507(unittest.TestCase):
    def test_good_sequence_is_recorded(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P105-07")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p105-tc07", result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertEqual(_MODULE.CASE, {
    "id": "TC-P105-07",
    "phase": "P105",
    "workstream": 14,
    "name": "Bokeh ordering and leakage",
    "intervention": "Render strong foreground defocus with bright lights behind an in-focus opaque subject.",
    "expected": "Respect layering and normalized energy while declaring unavoidable missing-background approximations.",
    "negative": "Uniform background blur with no foreground coverage model must fail.",
    "repeat": "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem.",
})
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "uniform-background-blur-without-foreground-coverage")
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["frameCount"], 8)
        self.assertTrue(math.isfinite(metrics["meanIntervalMs"]))
        self.assertTrue(math.isfinite(metrics["maxGapRelativeToNominal"]))
        self.assertTrue(math.isfinite(metrics["flicker"]))
        self.assertAlmostEqual(metrics["meanIntervalMs"], 40.0)

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(blurMode="uniform-background", foregroundCoverageModel=False))
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("uniform-background-blur-without-foreground-coverage", result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p105-tc07", result["preservedResults"])
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["frameCount"], 8)
        self.assertTrue(math.isfinite(metrics["meanIntervalMs"]))

    def test_different_evidence_id_is_preserved(self):
        evidence = "p105-tc07-repeat"
        result = evaluate(payload(evidenceId=evidence))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(evidence, result["preservedResults"])
        self.assertNotIn("p105-tc07", result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
