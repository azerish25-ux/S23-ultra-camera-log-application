"""Tests for TC-P105-01."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p105_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p105_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
STAMPS = [0, 40, 80, 120, 160, 200, 240, 280]
LUMA = [0.2, 0.22, 0.21, 0.23, 0.24, 0.22, 0.25, 0.23]


def payload(**overrides):
    base = {
        "evidenceId": "p105-tc01",
        "repeat": "translation",
        "nominalFramePeriodMs": 40,
        "frameTimestampsMs": list(STAMPS),
        "lumaMeans": list(LUMA),
        "hideGap": False,
        "useKeyframeAsBaseline": False,
        "keyframeScore": None,
        **{
        "objectShiftPx": 12,
        "historyShiftPx": 12
    },
    }
    base.update(overrides)
    return base


class TCP10501(unittest.TestCase):
    def test_good_sequence_is_recorded(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P105-01")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p105-tc01", result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertEqual(_MODULE.CASE, {
    "id": "TC-P105-01",
    "phase": "P105",
    "workstream": 14,
    "name": "History without reprojection",
    "intervention": "Move a known object while previous depth remains in its original pixel coordinates.",
    "expected": "Reject unaligned history or warp it correctly before temporal blending.",
    "negative": "A stationary-pixel average that leaves depth trails must fail.",
    "repeat": "Repeat translation, rotation, scale change, and camera motion.",
})
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "stationary-pixel-average-leaves-depth-trails")
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["frameCount"], 8)
        self.assertTrue(math.isfinite(metrics["meanIntervalMs"]))
        self.assertTrue(math.isfinite(metrics["maxGapRelativeToNominal"]))
        self.assertTrue(math.isfinite(metrics["flicker"]))
        self.assertAlmostEqual(metrics["meanIntervalMs"], 40.0)

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(objectShiftPx=12, historyShiftPx=0))
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("stationary-pixel-average-leaves-depth-trails", result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p105-tc01", result["preservedResults"])
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["frameCount"], 8)
        self.assertTrue(math.isfinite(metrics["meanIntervalMs"]))

    def test_different_evidence_id_is_preserved(self):
        evidence = "p105-tc01-repeat"
        result = evaluate(payload(evidenceId=evidence))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(evidence, result["preservedResults"])
        self.assertNotIn("p105-tc01", result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
