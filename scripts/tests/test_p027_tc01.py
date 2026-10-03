"""TC-P027-01 hidden audio omission is not a successful startup."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc01", Path(__file__).resolve().parents[1] / "gates" / "p027_tc01.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def payload(**overrides):
    base = {
        "order": "video-format-audio-format-samples",
        "pendingSamples": 0,
        "audioSelected": True,
        "videoPresent": True,
        "audioPresent": True,
        "stopRequested": False,
        "hidesAudioOmission": False,
        "withinBounds": True,
        "fabricatedSuccess": False,
        "takeId": "take-p027",
    }
    base.update(overrides)
    return base


class TcP02701(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_module_encodes_the_case_text(self):
        self.assertIn("user Stop", _MODULE.INTERVENTION)
        self.assertIn("without deadlock", _MODULE.EXPECTED)
        self.assertIn("hiding the omission", _MODULE.NEGATIVE)
        self.assertIn("video-format-audio-format-samples", _MODULE.ORDERS)
        self.assertIn("audio-format-video-format-samples", _MODULE.ORDERS)

    def test_zero_pending_samples_with_both_tracks_are_ready(self):
        result = evaluate(payload(pendingSamples=0))
        self.assertContract(result)
        self.assertEqual(result["decision"], "tracks_ready")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["take-p027", "video-format-audio-format-samples", "pending-samples:0", "video-track", "audio-track"],
        )
        self.assertTrue(any("pending zero" in item for item in result["reasons"]))

    def test_several_pending_samples_stop_honestly_on_the_other_order(self):
        result = evaluate(
            payload(
                order="audio-format-video-format-samples",
                pendingSamples=4,
                stopRequested=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("pending-samples:4", result["preservedResults"])
        self.assertIn("audio-track", result["preservedResults"])
        self.assertIn("video-track", result["preservedResults"])
        self.assertTrue(any("pending several" in item for item in result["reasons"]))
        self.assertTrue(any("audio-format-video-format-samples" in item for item in result["reasons"]))

    def test_hidden_audio_omission_with_video_alone_is_rejected(self):
        result = evaluate(
            payload(
                order="stop-before-audio-sample",
                pendingSamples=1,
                audioPresent=False,
                hidesAudioOmission=True,
                stopRequested=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "terminated", "tracks_ready"})
        self.assertEqual(result["rejectedClaims"], ["hidden-audio-omission"])
        self.assertIn("video-track", result["preservedResults"])
        self.assertNotIn("audio-track", result["preservedResults"])
        self.assertIn("take-p027", result["preservedResults"])

    def test_honest_omission_waits_and_keeps_the_video_track(self):
        result = evaluate(
            payload(audioPresent=False, hidesAudioOmission=False, pendingSamples=1)
        )
        self.assertEqual(result["decision"], "waiting")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("video-track", result["preservedResults"])
        self.assertNotIn("audio-track", result["preservedResults"])
        self.assertTrue(any("not hidden" in item for item in result["openQuestions"]))

    def test_fabricated_success_and_unbounded_wait_are_rejected(self):
        result = evaluate(payload(fabricatedSuccess=True, withinBounds=False, pendingSamples=3))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["fabricated-success", "unbounded-wait"])
        self.assertIn("audio-track", result["preservedResults"])
        self.assertIn("video-track", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "order": "later"},
            {**valid, "pendingSamples": -1},
            {**valid, "hidesAudioOmission": True},
            {**valid, "audioPresent": False, "videoPresent": False, "hidesAudioOmission": True},
            {k: v for k, v in valid.items() if k != "takeId"},
            {**valid, "extra": True},
            {**valid, "takeId": "Has Space"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
