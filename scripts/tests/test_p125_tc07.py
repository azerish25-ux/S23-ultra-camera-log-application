"""Tests for TC-P125-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
INTENDED = [0, 1, 2, 3, 4]


def payload(**overrides):
    base = {
        "evidenceId": "p125-timeline",
        "repeat": "fractional-rates",
        "intendedFrames": list(INTENDED),
        "assembledFrames": list(INTENDED),
        "overlapStart": 2,
        "overlapEnd": 3,
    }
    base.update(overrides)
    return base


class TCP12507(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-timeline"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Resume boundary duplication")
        self.assertEqual(_MODULE.NEGATIVE, "A playable movie with duplicated overlap frames must fail cadence integrity.")
        self.assertEqual(_MODULE.REPEAT, "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries.")

    def test_exact_timeline_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["assembledFrames"], INTENDED)
        self.assertTrue(result["preservedResults"][1]["emittedOnce"])

    def test_duplicated_overlap_fails_cadence(self):
        result = evaluate(payload(repeat="audio-bearing", assembledFrames=[0, 1, 2, 2, 3, 4]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DUP_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["intendedFrames"], INTENDED)

    def test_omitted_boundary_frame_is_rejected(self):
        result = evaluate(
            payload(evidenceId="p125-omit", repeat="scene-cuts", assembledFrames=[0, 1, 3, 4], overlapStart=2, overlapEnd=2)
        )
        self.assert_contract(result, "p125-omit")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OMIT_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.DUP_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(overlapEnd=1))
        with self.assertRaises(ValueError):
            evaluate(payload(assembledFrames=[0, True]))
