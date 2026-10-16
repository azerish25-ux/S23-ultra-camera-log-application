"""Tests for TC-P128-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _long_form(**overrides):
    value = {
        "expected_frames": 6,
        "accounted_frames": [0, 1, 2, 3, 4, 5],
        "checkpoint_frames": [0, 2, 5],
        "audio_duration": 0.25,
        "video_duration": 0.25,
        "audio_absent": False,
        "spot_check_only": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p128-evidence",
        "repeat": "Repeat",
        "playable": True,
        "overlapFrames": [2, 5],
        "frameRate": 23.976,
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12807(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frameAccount=", blob(result))
        self.assertTrue(result["reasons"])

    def test_exact_overlap_is_recorded_at_a_fractional_rate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frameRate=23.976", result["preservedResults"])
        self.assertIn("playable timeline emits each overlap frame once", result["reasons"])
        self.assertIn("frameAccount=6/6", blob(result))
        self.assertIn("checkpointChain=0<2<5", blob(result))

    def test_duplicated_overlap_in_a_playable_movie_is_rejected(self):
        result = evaluate(payload(accounted_frames=[0, 1, 2, 2, 3, 4, 5], overlapFrames=[2]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])
        self.assertIn("overlap frame 2 duplicated in a playable timeline", result["reasons"])

    def test_omitted_overlap_frame_is_rejected(self):
        result = evaluate(payload(accounted_frames=[0, 1, 2, 3, 4], overlapFrames=[5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OMITTED_TOKEN, result["rejectedClaims"])
        self.assertIn("missing-frame-index", result["rejectedClaims"])

    def test_audio_bearing_duration_mismatch_is_rejected(self):
        result = evaluate(payload(audio_duration=0.0, video_duration=0.05))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("audio-video-duration-mismatch", result["rejectedClaims"])

    def test_audio_absent_mismatch_stays_recorded(self):
        result = evaluate(payload(audio_duration=1, video_duration=5, audio_absent=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("audioVideoDelta=4", blob(result))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-cut"
        result = evaluate(payload(evidenceId=evidence, repeat="scene-cut"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
            evaluate(payload(frameRate=0))
