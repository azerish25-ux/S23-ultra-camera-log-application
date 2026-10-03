"""TC-P027-05 unbounded drain and complete truncated audio are rejected."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc05", Path(__file__).resolve().parents[1] / "gates" / "p027_tc05.py"
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
        "cause": "codec-failure",
        "waitedForever": False,
        "labelledComplete": False,
        "withinBound": True,
        "partialOutput": "partial-audio-p027",
        "incompleteStatus": True,
    }
    base.update(overrides)
    return base


class TcP02705(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("completing EOS", _MODULE.INTERVENTION)
        self.assertIn("incomplete status", _MODULE.EXPECTED)
        self.assertIn("Waiting forever", _MODULE.NEGATIVE)
        self.assertIn("codec-failure", _MODULE.CAUSES)
        self.assertIn("stopped-microphone", _MODULE.CAUSES)
        self.assertIn("blocked-mux", _MODULE.CAUSES)

    def test_codec_failure_stays_bounded_and_incomplete(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded_incomplete")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["partial-audio-p027", "codec-failure"])

    def test_stopped_microphone_is_a_separate_repeat(self):
        result = evaluate(payload(cause="stopped-microphone", partialOutput="mic-partial"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded_incomplete")
        self.assertEqual(result["preservedResults"], ["mic-partial", "stopped-microphone"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_waiting_forever_and_labelling_complete_are_rejected(self):
        result = evaluate(payload(cause="blocked-mux", waitedForever=True, labelledComplete=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded_incomplete"})
        self.assertEqual(
            result["rejectedClaims"],
            ["waited-forever", "truncated-audio-labelled-complete"],
        )
        self.assertIn("partial-audio-p027", result["preservedResults"])
        self.assertIn("blocked-mux", result["preservedResults"])

    def test_missing_incomplete_status_keeps_the_partial(self):
        result = evaluate(payload(withinBound=False, incompleteStatus=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["bound-missed", "missing-incomplete-status"])
        self.assertIn("partial-audio-p027", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "cause": "timeout"},
            {**valid, "partialOutput": ""},
            {**valid, "waitedForever": 1},
            {**valid, "labelledComplete": "false"},
            {k: v for k, v in valid.items() if k != "withinBound"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
