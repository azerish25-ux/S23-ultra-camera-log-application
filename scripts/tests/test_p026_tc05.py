"""TC-P026-05 drain timeout keeps partial output incomplete."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc05", Path(__file__).resolve().parents[1] / "gates" / "p026_tc05.py"
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
        "cause": "codec_failure",
        "boundMs": 500,
        "elapsedMs": 400,
        "otherTrackFinished": True,
        "waitedForever": False,
        "truncatedAudioComplete": False,
        "partialOutputId": "audio-aac-partial",
        "incompleteStatus": True,
    }
    base.update(overrides)
    return base


class TcP02605(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "complete"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("EOS", _MODULE.INTERVENTION)
        self.assertIn("incomplete status", _MODULE.EXPECTED)
        self.assertIn("Waiting forever", _MODULE.NEGATIVE)
        self.assertIn("codec_failure", _MODULE.CAUSES)
        self.assertIn("stopped_microphone", _MODULE.CAUSES)

    def test_codec_failure_stays_incomplete_inside_the_bound(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "incomplete")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("audio-aac-partial", result["preservedResults"])
        self.assertIn("elapsed:400", result["preservedResults"])
        self.assertTrue(any("codec_failure" in item for item in result["reasons"]))

    def test_stopped_microphone_stays_incomplete(self):
        result = evaluate(payload(cause="stopped_microphone"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "incomplete")
        self.assertIn("audio-aac-partial", result["preservedResults"])
        self.assertTrue(any("stopped_microphone" in item for item in result["reasons"]))

    def test_waiting_forever_is_rejected_and_keeps_partial_output(self):
        result = evaluate(payload(waitedForever=True, elapsedMs=900, cause="blocked_mux_writes"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("waited-forever", result["rejectedClaims"])
        self.assertIn("bound-exceeded", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "complete", "incomplete"})
        self.assertIn("audio-aac-partial", result["preservedResults"])

    def test_truncated_audio_labelled_complete_is_rejected(self):
        result = evaluate(payload(cause="stopped_microphone", truncatedAudioComplete=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["truncated-audio-complete"])
        self.assertIn("audio-aac-partial", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "complete"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "cause": "timeout"},
            {**valid, "boundMs": 0},
            {**valid, "waitedForever": "yes"},
            {**valid, "partialOutputId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
