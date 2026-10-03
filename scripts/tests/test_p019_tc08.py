"""TC-P019-08 double stop and repeated cleanup."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p019_tc08", Path(__file__).resolve().parents[1] / "gates" / "p019_tc08.py"
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
_TAKE = "take-exposure-1"


def payload(**overrides):
    base = {
        "scenario": "empty_startup",
        "events": ["stop", "close", "cancel", "detach", "close"],
        "takeId": _TAKE,
        "doubleRelease": False,
        "duplicatePublication": False,
        "secondTake": False,
    }
    base.update(overrides)
    return base


class TcP01908(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P019-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("redundant stop", _MODULE.INTERVENTION)
        self.assertIn("idempotent", _MODULE.EXPECTED)
        self.assertIn("second take", _MODULE.NEGATIVE)
        self.assertIn("empty_startup", _MODULE.SCENARIOS)
        self.assertIn("active_video", _MODULE.SCENARIOS)
        self.assertIn("active_audiovisual", _MODULE.SCENARIOS)
        self.assertIn("recovery_reopening", _MODULE.SCENARIOS)

    def test_empty_startup_cleanup_is_idempotent_for_one_take(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertEqual(result["preservedResults"].count(_TAKE), 1)
        self.assertTrue(any("publications:0" in item for item in result["reasons"]))
        self.assertTrue(any("close:1" in item for item in result["reasons"]))

    def test_active_video_publishes_once(self):
        result = evaluate(
            payload(scenario="active_video", events=["detach", "stop", "stop", "close"])
        )
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertTrue(any("publications:1" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_active_audiovisual_repeated_stop_stays_one_publication(self):
        result = evaluate(
            payload(scenario="active_audiovisual", events=["stop", "cancel", "stop"])
        )
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertTrue(any("publications:1" in item for item in result["reasons"]))

    def test_double_release_is_rejected_and_the_take_stays_singular(self):
        result = evaluate(payload(scenario="recovery_reopening", doubleRelease=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("double-release", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], [_TAKE])

    def test_duplicate_publication_and_second_take_are_rejected(self):
        result = evaluate(
            payload(
                scenario="active_video",
                duplicatePublication=True,
                secondTake=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["duplicate-publication", "second-take"])
        self.assertEqual(result["preservedResults"], [_TAKE])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "scenario": "idle"},
            {**valid, "events": []},
            {**valid, "events": ["halt"]},
            {**valid, "takeId": ""},
            {**valid, "doubleRelease": 1},
            {k: v for k, v in valid.items() if k != "scenario"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
