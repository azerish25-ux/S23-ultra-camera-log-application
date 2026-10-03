"""TC-P028-01 startup orderings do not hide a missing audio track."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc01", Path(__file__).resolve().parents[1] / "gates" / "p028_tc01.py"
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
        "order": ["video_format", "video_sample", "audio_format", "audio_sample", "stop"],
        "pendingSamples": 0,
        "boundMs": 1000,
        "elapsedMs": 100,
        "hideOmission": False,
    }
    base.update(overrides)
    return base


class TcP02801(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_module_encodes_the_case_text(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Reorder video and audio format callbacks and first sample arrival around a user Stop event.",
        )
        self.assertIn("terminate honestly", _MODULE.EXPECTED)
        self.assertIn("hiding the omission", _MODULE.NEGATIVE)

    def test_zero_pending_video_then_audio_then_stop_is_observed(self):
        result = evaluate(payload(pendingSamples=0))
        self.assertContract(result)
        self.assertEqual(result["decision"], "tracks_observed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("pending:0", result["preservedResults"])
        self.assertIn("selected:audio", result["preservedResults"])
        self.assertIn("event:stop", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_one_pending_audio_then_video_then_stop(self):
        result = evaluate(
            payload(
                pendingSamples=1,
                order=["audio_format", "audio_sample", "video_format", "video_sample", "stop"],
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "tracks_observed")
        self.assertIn("pending:1", result["preservedResults"])
        self.assertIn("arrived:audio", result["preservedResults"])
        self.assertIn("arrived:video", result["preservedResults"])

    def test_several_pending_stop_before_audio_terminates(self):
        result = evaluate(
            payload(
                pendingSamples=4,
                order=["video_format", "video_sample", "stop", "audio_format", "audio_sample"],
                elapsedMs=400,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminated")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "tracks_observed"})
        self.assertIn("pending:4", result["preservedResults"])
        self.assertIn("missing-audio", result["rejectedClaims"])
        self.assertIn("selected:audio", result["preservedResults"])
        self.assertIn("event:audio_format", result["preservedResults"])

    def test_hidden_video_only_omission_is_rejected(self):
        result = evaluate(
            payload(
                pendingSamples=0,
                order=["video_format", "video_sample", "stop"],
                hideOmission=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "terminated"})
        self.assertIn("hidden-audio-omission", result["rejectedClaims"])
        self.assertIn("video-only-selected-audio-take", result["rejectedClaims"])
        self.assertIn("selected:audio", result["preservedResults"])
        self.assertIn("selected:video", result["preservedResults"])
        self.assertIn("event:stop", result["preservedResults"])

    def test_waiting_inside_the_bound_does_not_fabricate_success(self):
        result = evaluate(
            payload(
                order=["video_format", "video_sample"],
                pendingSamples=1,
                elapsedMs=50,
                boundMs=1000,
            )
        )
        self.assertEqual(result["decision"], "waiting")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("selected:audio", result["preservedResults"])

    def test_elapsed_bound_terminates_without_deadlock(self):
        result = evaluate(
            payload(
                order=["video_format", "video_sample"],
                pendingSamples=4,
                elapsedMs=1000,
                boundMs=1000,
            )
        )
        self.assertEqual(result["decision"], "terminated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("pending:4", result["preservedResults"])
        self.assertTrue(any("terminated honestly" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "order": ["stop", "stop"]},
            {**valid, "pendingSamples": -1},
            {**valid, "hideOmission": True, "selectedTracks": ["video"]},
            {**valid, "selectedTracks": []},
            {k: v for k, v in valid.items() if k != "boundMs"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
