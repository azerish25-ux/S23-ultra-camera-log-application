"""TC-P036-05 writer pool saturation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc05", Path(__file__).resolve().parents[1] / "gates" / "p036_tc05.py"
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
        "queuedIds": ["raw-a", "raw-b"],
        "droppedIds": [],
        "stall": "short",
        "cancelled": False,
        "discardOldest": False,
        "recordingIndicator": True,
    }
    base.update(overrides)
    return base


class TcP03605(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("frame:raw-a", result["preservedResults"])
        self.assertIn("frame:raw-b", result["preservedResults"])

    def test_short_stall_stops_with_exact_accounting(self):
        result = evaluate(payload(stall="short"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("retained:2", result["preservedResults"])
        self.assertIn("stall:short", result["preservedResults"])
        self.assertIn("capacity:2", result["preservedResults"])
        self.assertNotIn("dropped:raw-a", result["preservedResults"])

    def test_prolonged_stall_stops_without_overwriting(self):
        result = evaluate(payload(stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("stall:prolonged", result["preservedResults"])
        self.assertIn("frame:raw-a", result["preservedResults"])
        self.assertIn("frame:raw-b", result["preservedResults"])
        self.assertTrue(any("prolonged" in item for item in result["reasons"]))

    def test_cancellation_during_full_pool_keeps_queued_samples(self):
        result = evaluate(payload(cancelled=True, stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "cancelled")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("frame:raw-a", result["preservedResults"])
        self.assertIn("frame:raw-b", result["preservedResults"])
        self.assertIn("cancelled", result["openQuestions"])

    def test_below_capacity_holds_samples(self):
        result = evaluate(payload(queuedIds=["raw-a"], capacity=2))
        self.assertEqual(result["decision"], "holding")
        self.assertIn("frame:raw-a", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_discard_oldest_fails_and_keeps_samples(self):
        result = evaluate(
            payload(
                queuedIds=["raw-b", "raw-c"],
                droppedIds=["raw-a"],
                discardOldest=True,
                recordingIndicator=True,
            )
        )
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stopped"})
        self.assertIn("discard-oldest-raw", result["rejectedClaims"])
        self.assertIn("recording-indicator-maintained", result["rejectedClaims"])
        self.assertIn("frame:raw-b", result["preservedResults"])
        self.assertIn("frame:raw-c", result["preservedResults"])
        self.assertIn("dropped:raw-a", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "capacity": 0},
            {**valid, "queuedIds": ["raw-a", "raw-b", "raw-c"]},
            {**valid, "discardOldest": True},
            {**valid, "stall": "forever"},
            {**valid, "cancelled": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
