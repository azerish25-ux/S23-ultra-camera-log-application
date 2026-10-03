"""TC-P040-05 writer pool saturation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p040_tc05", Path(__file__).resolve().parents[1] / "gates" / "p040_tc05.py"
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
        "queuedIds": ["a", "b"],
        "droppedIds": [],
        "stall": "short",
        "cancelled": False,
        "discardOldest": False,
        "recordingIndicator": False,
    }
    base.update(overrides)
    return base


class TcP04005(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P040-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_intervention_expected_and_negative_are_encoded(self):
        self.assertIn("preallocated source-copy capacity", _MODULE.INTERVENTION)
        self.assertIn("exact retained-frame accounting", _MODULE.EXPECTED)
        self.assertIn("oldest RAW record", _MODULE.NEGATIVE)

    def test_short_stall_stops_at_capacity_without_overwrite(self):
        result = evaluate(payload(stall="short"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("capacity:2", result["preservedResults"])
        self.assertIn("stall:short", result["preservedResults"])
        self.assertIn("retained:2", result["preservedResults"])
        self.assertIn("frame:a", result["preservedResults"])
        self.assertIn("frame:b", result["preservedResults"])
        self.assertIn("pool exhausted", result["openQuestions"])
        self.assertIn("exact retained count 2", result["reasons"])

    def test_prolonged_stall_stops_with_the_same_frames(self):
        result = evaluate(payload(stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("stall:prolonged", result["preservedResults"])
        self.assertIn("frame:a", result["preservedResults"])
        self.assertIn("frame:b", result["preservedResults"])
        self.assertTrue(any("prolonged" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_cancellation_during_the_full_pool_keeps_queued_samples(self):
        result = evaluate(payload(cancelled=True, stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "cancelled")
        self.assertIn("frame:a", result["preservedResults"])
        self.assertIn("frame:b", result["preservedResults"])
        self.assertIn("retained:2", result["preservedResults"])
        self.assertIn("cancelled", result["openQuestions"])
        self.assertTrue(any("full" in item for item in result["reasons"]))
        self.assertNotIn("dropped:a", result["preservedResults"])

    def test_negative_discard_oldest_fails(self):
        result = evaluate(
            payload(
                queuedIds=["b"],
                droppedIds=["a"],
                discardOldest=True,
                recordingIndicator=True,
                stall="short",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stopped"})
        self.assertEqual(
            result["rejectedClaims"],
            ["discard-oldest-raw", "recording-indicator-maintained"],
        )
        self.assertIn("frame:b", result["preservedResults"])
        self.assertIn("dropped:a", result["preservedResults"])
        self.assertIn("retained:1", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_holding_below_capacity_does_not_invent_a_stop(self):
        result = evaluate(payload(capacity=3, queuedIds=["a", "b"], stall="short"))
        self.assertEqual(result["decision"], "holding")
        self.assertIn("retained:2", result["preservedResults"])
        self.assertIn("frame:a", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stopped"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "stall"},
            {**valid, "extra": True},
            {**valid, "capacity": 0},
            {**valid, "queuedIds": ["a", "a"]},
            {**valid, "queuedIds": ["a", "b", "c"]},
            {**valid, "discardOldest": True},
            {**valid, "droppedIds": ["a"], "queuedIds": ["a"], "discardOldest": True},
            {**valid, "stall": "forever"},
            {**valid, "cancelled": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
