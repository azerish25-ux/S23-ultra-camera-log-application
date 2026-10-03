"""TC-P020-08 cleanup is idempotent and keeps one take."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc08", Path(__file__).resolve().parents[1] / "gates" / "p020_tc08.py"
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
        "events": ["stop", "close"],
        "takeId": "take-wb-1",
        "doubleRelease": False,
        "duplicatePublication": False,
        "secondTake": False,
    }
    base.update(overrides)
    return base


class TcP02008(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P020-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def assertInventory(self, result):
        for item in _MODULE.WB_INVENTORY:
            self.assertIn(item, result["preservedResults"])
        self.assertEqual(result["preservedResults"].count("take:take-wb-1"), 1)
        self.assertIn("creative.slider:warm", result["preservedResults"])
        self.assertIn("hardware.kelvin:unavailable", result["preservedResults"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("different orders", _MODULE.INTERVENTION)
        self.assertIn("single coherent terminal take", _MODULE.EXPECTED)
        self.assertIn("second take", _MODULE.NEGATIVE)
        self.assertIn("empty_startup", _MODULE.REPEATS)
        self.assertIn("active_video", _MODULE.REPEATS)
        self.assertIn("active_audiovisual", _MODULE.REPEATS)
        self.assertIn("recovery_reopening", _MODULE.REPEATS)

    def test_empty_startup_stop_then_close_is_idempotent(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertInventory(result)
        self.assertTrue(any("empty_startup" in item for item in result["reasons"]))
        self.assertTrue(any("single terminal take take-wb-1" in item for item in result["reasons"]))

    def test_active_video_close_detach_stop_is_also_idempotent(self):
        result = evaluate(payload(scenario="active_video", events=["close", "detach", "stop"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertInventory(result)
        self.assertTrue(any("active_video" in item for item in result["reasons"]))
        self.assertTrue(any("close,detach,stop" in item for item in result["reasons"]))

    def test_double_release_during_audiovisual_capture_is_rejected(self):
        result = evaluate(payload(scenario="active_audiovisual", doubleRelease=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "idempotent"})
        self.assertEqual(result["rejectedClaims"], ["double-release"])
        self.assertInventory(result)

    def test_second_take_on_recovery_reopening_is_rejected(self):
        result = evaluate(
            payload(
                scenario="recovery_reopening",
                events=["cancel", "detach", "close"],
                secondTake=True,
                duplicatePublication=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("second-take", result["rejectedClaims"])
        self.assertIn("duplicate-publication", result["rejectedClaims"])
        self.assertInventory(result)
        self.assertIn("source.metadata:unchanged", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "scenario": "idle"},
            {**valid, "events": []},
            {**valid, "events": ["halt"]},
            {**valid, "doubleRelease": 1},
            {**valid, "takeId": ""},
            {k: v for k, v in valid.items() if k != "takeId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
