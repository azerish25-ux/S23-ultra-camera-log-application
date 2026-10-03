"""TC-P035-05 writer pool saturation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc05", Path(__file__).resolve().parents[1] / "gates" / "p035_tc05.py"
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
        "capacity": 2,
        "queuedIds": ["f0", "f1"],
        "stall": "prolonged",
        "cancel": False,
        "discardOldest": False,
        "indicator": "stopped",
    }
    base.update(overrides)
    return base


class TcP03505(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_repeat_short_stall_holds_frames(self):
        result = evaluate(
            payload(stall="short", queuedIds=["f0"], capacity=2, indicator="recording")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "held")
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("retained:1", result["preservedResults"])
        self.assertIn("stall:short", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_prolonged_stall_stops_full_pool(self):
        result = evaluate(payload(stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])
        self.assertIn("retained:2", result["preservedResults"])
        self.assertIn("capacity:2", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_repeat_cancel_during_full_pool(self):
        result = evaluate(payload(cancel=True, stall="prolonged"))
        self.assertEqual(result["decision"], "cancelled")
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])
        self.assertIn("retained:2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_discard_oldest_keeps_every_id(self):
        result = evaluate(payload(discardOldest=True, indicator="recording"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["discard-oldest-raw", "indicator-maintained-by-discard"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])
        self.assertIn("retained:2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "capacity": 0},
            {**valid, "queuedIds": ["f0", "f0"]},
            {**valid, "queuedIds": ["f0", "f1", "f2"]},
            {**valid, "cancel": True, "queuedIds": ["f0"]},
            {**valid, "stall": "forever"},
            {key: value for key, value in valid.items() if key != "indicator"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
