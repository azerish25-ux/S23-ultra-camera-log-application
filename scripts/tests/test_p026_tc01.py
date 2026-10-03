"""TC-P026-01 startup permutations do not hide a missing audio track."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc01", Path(__file__).resolve().parents[1] / "gates" / "p026_tc01.py"
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
        "ordering": "stop_between_callbacks",
        "pendingSamples": "zero",
        "audioSelected": True,
        "videoReady": True,
        "audioReady": False,
        "userStop": True,
        "hidesAudioOmission": False,
        "deadlocked": False,
        "fabricatedSuccess": False,
        "withinBounds": True,
        "takeId": "take-p026",
        "videoEvidence": "video-access-unit",
    }
    base.update(overrides)
    return base


class TcP02601(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("user Stop", _MODULE.INTERVENTION)
        self.assertIn("within bounds", _MODULE.EXPECTED)
        self.assertIn("hiding the omission", _MODULE.NEGATIVE)
        self.assertIn("zero", _MODULE.PENDING_COUNTS)
        self.assertIn("several", _MODULE.PENDING_COUNTS)

    def test_zero_pending_samples_terminates_honestly(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("take-p026", result["preservedResults"])
        self.assertIn("video-access-unit", result["preservedResults"])
        self.assertIn("pending:zero", result["preservedResults"])

    def test_several_pending_samples_still_terminate_without_audio(self):
        result = evaluate(
            payload(ordering="video_then_audio_then_samples", pendingSamples="several")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminated")
        self.assertIn("pending:several", result["preservedResults"])
        self.assertIn("video-access-unit", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "tracks_ready"})

    def test_one_pending_sample_can_mark_required_tracks_ready(self):
        result = evaluate(
            payload(
                ordering="audio_then_video_then_samples",
                pendingSamples="one",
                audioReady=True,
                userStop=False,
            )
        )
        self.assertEqual(result["decision"], "tracks_ready")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("pending:one", result["preservedResults"])
        self.assertIn("video-access-unit", result["preservedResults"])

    def test_hidden_audio_omission_is_rejected(self):
        result = evaluate(payload(hidesAudioOmission=True, pendingSamples="one"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "tracks_ready", "terminated"})
        self.assertEqual(result["rejectedClaims"], ["hidden-audio-omission"])
        self.assertIn("video-access-unit", result["preservedResults"])
        self.assertIn("take-p026", result["preservedResults"])

    def test_fabricated_success_and_deadlock_are_rejected(self):
        result = evaluate(payload(fabricatedSuccess=True, deadlocked=True, withinBounds=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["deadlock", "fabricated-success", "bounds-exceeded"],
        )
        self.assertIn("video-access-unit", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "ordering": "later"},
            {**valid, "pendingSamples": "two"},
            {k: v for k, v in valid.items() if k != "videoEvidence"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
