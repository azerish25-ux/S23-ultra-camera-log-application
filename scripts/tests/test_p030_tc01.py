"""TC-P030-01 track startup permutation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p030_tc01", Path(__file__).resolve().parents[1] / "gates" / "p030_tc01.py"
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
        "selectedTracks": ["video", "audio"],
        "order": ["video_format", "audio_format", "video_sample", "audio_sample", "stop"],
        "pendingSamples": 0,
        "boundMs": 200,
        "elapsedMs": 10,
        "hideOmission": False,
    }
    base.update(overrides)
    return base


class TcP03001(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P030-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_pending_zero_observes_both_tracks_without_success(self):
        source = payload(pendingSamples=0)
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "tracks_observed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertIn("pending:0", result["preservedResults"])
        self.assertIn("arrived:video", result["preservedResults"])
        self.assertIn("arrived:audio", result["preservedResults"])
        self.assertIn("event:stop", result["preservedResults"])
        self.assertEqual(_MODULE.INTERVENTION[:8], "Reorder ")
        self.assertIn("fabricated success", _MODULE.EXPECTED)

    def test_pending_one_stops_before_audio_sample(self):
        source = payload(
            pendingSamples=1,
            order=["video_format", "video_sample", "audio_format", "stop"],
        )
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminated")
        self.assertEqual(result["rejectedClaims"], ["missing-audio"])
        self.assertIn("pending:1", result["preservedResults"])
        self.assertIn("arrived:video", result["preservedResults"])
        self.assertNotIn("arrived:audio", result["preservedResults"])
        self.assertIn("event:audio_format", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["missing audio"])

    def test_pending_several_with_stop_before_any_sample(self):
        source = payload(pendingSamples=4, order=["stop"], elapsedMs=200)
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminated")
        self.assertEqual(result["rejectedClaims"], ["missing-video", "missing-audio"])
        self.assertIn("pending:4", result["preservedResults"])
        self.assertIn("selected:audio", result["preservedResults"])
        self.assertNotIn("arrived:video", result["preservedResults"])
        self.assertNotIn("arrived:audio", result["preservedResults"])

    def test_audio_first_ordering_with_zero_pending_is_not_success(self):
        source = payload(
            pendingSamples=0,
            order=["audio_format", "audio_sample", "video_format", "video_sample", "stop"],
        )
        result = evaluate(source)
        self.assertEqual(result["decision"], "tracks_observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("arrived:audio", result["preservedResults"])
        self.assertIn("arrived:video", result["preservedResults"])

    def test_negative_video_only_hides_selected_audio(self):
        source = payload(
            order=["video_format", "video_sample", "stop"],
            hideOmission=True,
            pendingSamples=0,
        )
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["rejectedClaims"],
            ["hidden-audio-omission", "video-only-selected-audio-take"],
        )
        self.assertIn("selected:audio", result["preservedResults"])
        self.assertIn("event:video_sample", result["preservedResults"])
        self.assertIn("pending:0", result["preservedResults"])
        self.assertIn("arrived:video", result["preservedResults"])
        self.assertNotIn("arrived:audio", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_waiting_inside_bound_does_not_fabricate_success(self):
        result = evaluate(
            payload(order=["video_format", "video_sample"], pendingSamples=1, elapsedMs=10)
        )
        self.assertEqual(result["decision"], "waiting")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "tracks_observed"})
        self.assertIn("pending:1", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["required tracks still pending"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "order"},
            {**valid, "extra": True},
            {**valid, "pendingSamples": -1},
            {**valid, "pendingSamples": True},
            {**valid, "boundMs": 0},
            {**valid, "hideOmission": "true"},
            {**valid, "selectedTracks": ["video"], "hideOmission": True},
            {**valid, "order": ["stop", "stop"]},
            {**valid, "selectedTracks": []},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
