"""TC-P017-08 double stop and repeated cleanup."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc08", Path(__file__).resolve().parents[1] / "gates" / "p017_tc08.py"
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
_TAKE = "take-17"


def payload(**overrides):
    base = {
        "scenario": "empty_startup",
        "events": ["stop", "close", "stop"],
        "takeId": _TAKE,
        "doubleRelease": False,
        "duplicatePublication": False,
        "secondTakeFromCleanup": False,
    }
    base.update(overrides)
    return base


class TcP01708(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("different orders", _MODULE.INTERVENTION)
        self.assertIn("idempotent", _MODULE.EXPECTED)
        self.assertIn("second take", _MODULE.NEGATIVE)
        self.assertIn("active_video", _MODULE.SCENARIOS)
        self.assertIn("recovery_reopening", _MODULE.SCENARIOS)

    def test_empty_startup_repeated_stop_keeps_one_take(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertEqual(result["preservedResults"].count(_TAKE), 1)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("empty_startup" in item for item in result["reasons"]))
        self.assertTrue(any("stop>close>stop" in item for item in result["reasons"]))
        self.assertTrue(any("cleanup is idempotent" in item for item in result["reasons"]))

    def test_active_video_detach_then_close_is_one_take(self):
        result = evaluate(
            payload(
                scenario="active_video",
                events=["stop", "detach", "close", "cancel", "close"],
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertTrue(any("active_video" in item for item in result["reasons"]))
        self.assertTrue(any("detach" in item for item in result["reasons"]))

    def test_active_audiovisual_cleanup_does_not_duplicate_the_take(self):
        result = evaluate(
            payload(scenario="active_audiovisual", events=["cancel", "stop", "close"])
        )
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertEqual(len(result["preservedResults"]), 1)

    def test_recovery_reopening_preserves_the_terminal_identity(self):
        result = evaluate(
            payload(scenario="recovery_reopening", events=["detach", "close", "detach"])
        )
        self.assertEqual(result["decision"], "idempotent")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], [_TAKE])

    def test_double_release_is_rejected_without_a_second_take(self):
        result = evaluate(payload(scenario="active_video", doubleRelease=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["double-release"])
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_duplicate_publication_and_second_take_are_rejected(self):
        result = evaluate(
            payload(
                scenario="recovery_reopening",
                duplicatePublication=True,
                secondTakeFromCleanup=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["duplicate-publication", "second-take"],
        )
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertEqual(result["preservedResults"].count(_TAKE), 1)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "scenario": "paused"},
            {**valid, "events": []},
            {**valid, "events": ["stop", "flush"]},
            {**valid, "takeId": ""},
            {**valid, "doubleRelease": 1},
            {**valid, "secondTakeFromCleanup": "no"},
            {k: v for k, v in valid.items() if k != "events"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
