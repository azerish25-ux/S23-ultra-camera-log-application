"""TC-P018-08 double stop and repeated cleanup."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p018_tc08", Path(__file__).resolve().parents[1] / "gates" / "p018_tc08.py"
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
        "scenario": "empty_startup",
        "events": ["stop", "close", "stop"],
        "takeId": "take-empty",
        "doubleRelease": False,
        "duplicatePublication": False,
        "secondTake": False,
    }
    base.update(overrides)
    return base


class TcP01808(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P018-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_contract(self):
        self.assertIn("different orders", _MODULE.INTERVENTION)
        self.assertIn("single coherent terminal take identity", _MODULE.EXPECTED)
        self.assertIn("second take", _MODULE.NEGATIVE)
        self.assertIn("empty startup", _MODULE.REPEAT)
        self.assertIn("active video", _MODULE.REPEAT)

    def test_empty_startup_cleanup_is_idempotent(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], ["take-empty"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("close:1" == item for item in result["reasons"]))
        self.assertTrue(any("stop:1" == item for item in result["reasons"]))
        self.assertTrue(any("publications:0" == item for item in result["reasons"]))

    def test_active_video_detach_order_keeps_one_take(self):
        result = evaluate(
            payload(
                scenario="active_video",
                events=["detach", "cancel", "close", "detach"],
                takeId="take-video",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], ["take-video"])
        self.assertTrue(any("detach:1" == item for item in result["reasons"]))
        self.assertTrue(any("publications:0" == item for item in result["reasons"]))

    def test_active_audiovisual_stop_publishes_once(self):
        result = evaluate(
            payload(
                scenario="active_audiovisual",
                events=["stop", "close", "cancel", "detach", "stop", "close"],
                takeId="take-av",
            )
        )
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], ["take-av"])
        self.assertTrue(any("publications:1" == item for item in result["reasons"]))
        self.assertEqual(result["preservedResults"].count("take-av"), 1)

    def test_recovery_reopening_does_not_create_another_take(self):
        result = evaluate(
            payload(
                scenario="recovery_reopening",
                events=["cancel", "detach", "close"],
                takeId="take-recover",
            )
        )
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], ["take-recover"])

    def test_double_release_duplicate_publication_and_second_take_are_rejected(self):
        result = evaluate(
            payload(
                scenario="active_video",
                events=["stop", "close"],
                takeId="take-video",
                doubleRelease=True,
                duplicatePublication=True,
                secondTake=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["rejectedClaims"],
            ["double-release", "duplicate-publication", "second-take"],
        )
        self.assertEqual(result["preservedResults"], ["take-video"])
        self.assertNotIn("take-video-2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "scenario": "live"},
            {**valid, "events": []},
            {**valid, "events": ["stop", "publish"]},
            {**valid, "takeId": ""},
            {**valid, "doubleRelease": 1},
            {k: v for k, v in valid.items() if k != "events"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
