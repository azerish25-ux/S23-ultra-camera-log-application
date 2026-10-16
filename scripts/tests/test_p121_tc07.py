"""Tests for TC-P121-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-boundary",
        "repeat": "fractional-rate",
        "intendedFrames": [0, 1, 2, 3, 4],
        "assembledFrames": [0, 1, 2, 3, 4],
        "overlapFrames": [2],
        "audioPresent": False,
        "sceneCutFrame": None,
    }
    base.update(overrides)
    return base


class TCP12107(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-boundary"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Resume boundary duplication")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Assemble chunks whose temporal overlap contains repeated or omitted output frames.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Emit the exact intended timeline once and maintain declared temporal continuity.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "A playable movie with duplicated overlap frames must fail cadence integrity.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries.",
        )

    def test_exact_timeline_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["emittedOnce"])
        self.assertEqual(result["preservedResults"][1]["intendedFrames"], [0, 1, 2, 3, 4])

    def test_duplicated_overlap_fails_even_if_playable(self):
        result = evaluate(payload(assembledFrames=[0, 1, 2, 2, 3, 4]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DUPLICATE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["assembledFrames"], [0, 1, 2, 2, 3, 4])
        self.assertFalse(result["preservedResults"][1]["emittedOnce"])

    def test_omitted_boundary_and_audio_and_scene_cut(self):
        omitted = evaluate(payload(assembledFrames=[0, 1, 2, 4], overlapFrames=[2, 3]))
        self.assertEqual(omitted["decision"], "rejected")
        self.assertIn("omitted-boundary-frames", omitted["rejectedClaims"])
        audio = evaluate(
            payload(
                evidenceId="p121-audio-boundary",
                repeat="audio-bearing",
                audioPresent=True,
            )
        )
        self.assert_contract(audio, "p121-audio-boundary")
        self.assertEqual(audio["decision"], "recorded")
        self.assertTrue(audio["preservedResults"][1]["audioPresent"])
        cut = evaluate(
            payload(
                repeat="scene-cut",
                assembledFrames=[0, 1, 2, 2, 3, 4],
                sceneCutFrame=2,
            )
        )
        self.assertEqual(cut["decision"], "rejected")
        self.assertIn(_MODULE.DUPLICATE_TOKEN, cut["rejectedClaims"])
        self.assertTrue(any("scene cut" in item for item in cut["reasons"]))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(intendedFrames=[0, 2, 3]))
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="audio-bearing", audioPresent=False))
