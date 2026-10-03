"""TC-P021-08 double stop and repeated cleanup."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc08", Path(__file__).resolve().parents[1] / "gates" / "p021_tc08.py"
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
_TAKE = "take-7"


def payload(**overrides):
    base = {
        "scenario": "empty_startup",
        "events": ["stop", "close"],
        "takeId": _TAKE,
        "doubleRelease": False,
        "duplicatePublication": False,
        "secondTake": False,
    }
    base.update(overrides)
    return base


class TcP02108(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _MODULE.FOCUS_INVENTORY:
            self.assertIn(token, result["preservedResults"])
        self.assertEqual(result["preservedResults"].count("take:" + _TAKE), 1)

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("redundant stop, close, cancellation, and detach", _MODULE.INTERVENTION)
        self.assertIn("single coherent terminal take", _MODULE.EXPECTED)
        self.assertIn("second take created by cleanup", _MODULE.NEGATIVE)
        for name in ("empty_startup", "active_video", "active_audiovisual", "recovery_reopening"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_repeat_empty_startup_is_idempotent(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("empty_startup" in item for item in result["reasons"]))
        self.assertIn("physical.distance:unknown", result["preservedResults"])

    def test_repeat_active_video_different_event_order(self):
        result = evaluate(
            payload(scenario="active_video", events=["detach", "cancel", "stop", "close", "stop"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"].count("take:" + _TAKE), 1)
        self.assertTrue(any("active_video" in item for item in result["reasons"]))
        self.assertIn("virtual.subject:face", result["preservedResults"])

    def test_repeat_audiovisual_and_recovery(self):
        for scenario in ("active_audiovisual", "recovery_reopening"):
            result = evaluate(payload(scenario=scenario, events=["close", "detach", "cancel"]))
            self.assertContract(result)
            self.assertEqual(result["decision"], "idempotent")
            self.assertTrue(any(scenario in item for item in result["reasons"]))

    def test_negative_double_release_keeps_one_take(self):
        result = evaluate(payload(doubleRelease=True, scenario="active_video"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "idempotent"})
        self.assertIn("double-release", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"].count("take:" + _TAKE), 1)

    def test_negative_duplicate_publication_and_second_take(self):
        result = evaluate(
            payload(
                scenario="recovery_reopening",
                duplicatePublication=True,
                secondTake=True,
                events=["stop", "stop"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("duplicate-publication", result["rejectedClaims"])
        self.assertIn("second-take", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"].count("take:" + _TAKE), 1)
        self.assertIn("physical.subject:nearby_foreground", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "scenario": "preview"},
            {**valid, "events": []},
            {**valid, "events": ["halt"]},
            {**valid, "takeId": ""},
            {**valid, "secondTake": "yes"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
