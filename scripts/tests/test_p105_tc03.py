"""Tests for TC-P105-03."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p105_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p105_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
STAMPS = [0, 40, 80, 120, 160, 200, 240, 280]
LUMA = [0.2, 0.22, 0.21, 0.23, 0.24, 0.22, 0.25, 0.23]


def payload(**overrides):
    base = {
        "evidenceId": "p105-tc03",
        "repeat": "stationary-background",
        "nominalFramePeriodMs": 40,
        "frameTimestampsMs": list(STAMPS),
        "lumaMeans": list(LUMA),
        "hideGap": False,
        "useKeyframeAsBaseline": False,
        "keyframeScore": None,
        **{
        "normalization": "aligned-relative"
    },
    }
    base.update(overrides)
    return base


class TCP10503(unittest.TestCase):
    def test_good_sequence_is_recorded(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P105-03")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p105-tc03", result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertEqual(_MODULE.CASE, {
    "id": "TC-P105-03",
    "phase": "P105",
    "workstream": 14,
    "name": "Relative-scale pumping",
    "intervention": "Introduce a near object or scene-content change that alters raw model depth normalization.",
    "expected": "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts.",
    "negative": "Independent min-max normalization per frame must fail.",
    "repeat": "Repeat stationary backgrounds with changing foreground occupancy.",
})
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "independent-min-max-normalization-per-frame")
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["frameCount"], 8)
        self.assertTrue(math.isfinite(metrics["meanIntervalMs"]))
        self.assertTrue(math.isfinite(metrics["maxGapRelativeToNominal"]))
        self.assertTrue(math.isfinite(metrics["flicker"]))
        self.assertAlmostEqual(metrics["meanIntervalMs"], 40.0)

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(normalization="independent-minmax"))
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("independent-min-max-normalization-per-frame", result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p105-tc03", result["preservedResults"])
        metrics = result["preservedResults"][1]
        self.assertEqual(metrics["frameCount"], 8)
        self.assertTrue(math.isfinite(metrics["meanIntervalMs"]))

    def test_different_evidence_id_is_preserved(self):
        evidence = "p105-tc03-repeat"
        result = evaluate(payload(evidenceId=evidence))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(evidence, result["preservedResults"])
        self.assertNotIn("p105-tc03", result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
