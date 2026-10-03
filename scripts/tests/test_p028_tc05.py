"""TC-P028-05 drain ends inside the bound and stays incomplete."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc05", Path(__file__).resolve().parents[1] / "gates" / "p028_tc05.py"
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
_PARTIAL = "private-stage/take-p028.mp4"


def payload(**overrides):
    base = {
        "boundMs": 1500,
        "elapsedMs": 400,
        "videoEos": True,
        "audioEos": False,
        "failureMode": "codec_failure",
        "waitForever": False,
        "labelTruncatedAudioComplete": False,
        "partialOutput": [_PARTIAL],
    }
    base.update(overrides)
    return base


class TcP02805(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("completing EOS", _MODULE.INTERVENTION)
        self.assertIn("incomplete status", _MODULE.EXPECTED)
        self.assertIn("Waiting forever", _MODULE.NEGATIVE)

    def test_codec_failure_stays_incomplete_inside_the_bound(self):
        result = evaluate(payload(failureMode="codec_failure"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "incomplete")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "drained"})
        self.assertIn("codec_failure", result["rejectedClaims"])
        self.assertIn(_PARTIAL, result["preservedResults"])
        self.assertIn("audioEos:false", result["preservedResults"])
        self.assertIn("videoEos:true", result["preservedResults"])

    def test_stopped_microphone_stays_incomplete(self):
        result = evaluate(payload(failureMode="stopped_microphone", elapsedMs=200))
        self.assertEqual(result["decision"], "incomplete")
        self.assertIn("stopped_microphone", result["rejectedClaims"])
        self.assertIn(_PARTIAL, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_blocked_mux_write_stays_incomplete(self):
        result = evaluate(payload(failureMode="blocked_mux", elapsedMs=1500))
        self.assertEqual(result["decision"], "incomplete")
        self.assertIn("blocked_mux", result["rejectedClaims"])
        self.assertIn(_PARTIAL, result["preservedResults"])
        self.assertIn("bound:1500", result["preservedResults"])

    def test_waiting_forever_is_rejected(self):
        result = evaluate(payload(failureMode="none", waitForever=True, elapsedMs=10))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "incomplete", "drained"})
        self.assertIn("wait-forever", result["rejectedClaims"])
        self.assertIn(_PARTIAL, result["preservedResults"])

    def test_labelling_truncated_audio_complete_is_rejected(self):
        result = evaluate(
            payload(failureMode="none", labelTruncatedAudioComplete=True, elapsedMs=100)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "drained"})
        self.assertIn("truncated-audio-labelled-complete", result["rejectedClaims"])
        self.assertIn(_PARTIAL, result["preservedResults"])
        self.assertIn("audioEos:false", result["preservedResults"])

    def test_elapsed_past_the_bound_is_rejected(self):
        result = evaluate(payload(failureMode="none", elapsedMs=1501))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("bound-exceeded", result["rejectedClaims"])
        self.assertIn(_PARTIAL, result["preservedResults"])

    def test_both_tracks_inside_the_bound_are_not_a_certificate(self):
        result = evaluate(
            payload(failureMode="none", videoEos=True, audioEos=True, elapsedMs=800)
        )
        self.assertEqual(result["decision"], "drained")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_PARTIAL, result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "failureMode": "timeout"},
            {**valid, "boundMs": 0},
            {**valid, "waitForever": "yes"},
            {**valid, "partialOutput": ["", "clip"]},
            {k: v for k, v in valid.items() if k != "audioEos"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
