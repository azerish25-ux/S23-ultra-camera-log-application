"""TC-P025-05 drain timeout."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p025_tc05", Path(__file__).resolve().parents[1] / "gates" / "p025_tc05.py"
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
        "boundMs": 200,
        "elapsedMs": 40,
        "videoEos": True,
        "audioEos": False,
        "failureMode": "none",
        "waitForever": False,
        "labelTruncatedAudioComplete": False,
        "partialOutput": ["video-access-unit"],
    }
    base.update(overrides)
    return base


class TcP02505(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P025-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_audio_eos_missing_is_incomplete_inside_the_bound(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "incomplete")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("video-access-unit", result["preservedResults"])
        self.assertIn("audioEos:false", result["preservedResults"])
        self.assertIn("bound:200", result["preservedResults"])
        self.assertIn("output is incomplete", result["openQuestions"])

    def test_codec_failure_keeps_partial_output(self):
        result = evaluate(payload(failureMode="codec_failure", partialOutput=["codec-buffer"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "incomplete")
        self.assertIn("codec_failure", result["rejectedClaims"])
        self.assertIn("codec-buffer", result["preservedResults"])

    def test_stopped_microphone_keeps_partial_output(self):
        result = evaluate(
            payload(failureMode="stopped_microphone", partialOutput=["pcm-prefix"])
        )
        self.assertEqual(result["decision"], "incomplete")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("stopped_microphone", result["rejectedClaims"])
        self.assertIn("pcm-prefix", result["preservedResults"])

    def test_blocked_mux_writes_keep_partial_output(self):
        result = evaluate(payload(failureMode="blocked_mux", partialOutput=["mux-page"]))
        self.assertEqual(result["decision"], "incomplete")
        self.assertIn("blocked_mux", result["rejectedClaims"])
        self.assertIn("mux-page", result["preservedResults"])
        self.assertIn("elapsed:40", result["preservedResults"])

    def test_negative_wait_forever_fails_and_keeps_partial_output(self):
        result = evaluate(payload(waitForever=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "drained"})
        self.assertIn("wait-forever", result["rejectedClaims"])
        self.assertIn("video-access-unit", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_negative_truncated_audio_must_not_be_labelled_complete(self):
        result = evaluate(payload(labelTruncatedAudioComplete=True, audioEos=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("truncated-audio-labelled-complete", result["rejectedClaims"])
        self.assertIn("audioEos:false", result["preservedResults"])
        self.assertIn("video-access-unit", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "boundMs": 0},
            {**valid, "elapsedMs": -1},
            {**valid, "failureMode": "timeout"},
            {**valid, "videoEos": 1},
            {**valid, "partialOutput": [""]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
