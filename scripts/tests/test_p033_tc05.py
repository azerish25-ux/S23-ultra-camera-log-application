"""TC-P033-05 writer pool saturation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc05", Path(__file__).resolve().parents[1] / "gates" / "p033_tc05.py"
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
_FORBIDDEN = {"qualified", "allowed"}


def payload(**overrides):
    base = {
        "capacity": 3,
        "queuedIds": ["raw-0", "raw-1", "raw-2"],
        "retained": 3,
        "stall": "short",
        "cancelled": False,
        "discardOldest": False,
        "indicatorOn": True,
        "overwrittenIds": [],
    }
    base.update(overrides)
    return base


class TcP03305(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-05")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])
        for item in ("raw-0", "raw-1", "raw-2"):
            self.assertIn("queued:" + item, result["preservedResults"])

    def test_repeat_short_stall_stops_with_exact_account(self):
        result = evaluate(payload(stall="short"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("retained-expected:3", result["preservedResults"])
        self.assertIn("retained-claimed:3", result["preservedResults"])
        self.assertIn("stall:short", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertEqual(result["openQuestions"], [])
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_repeat_prolonged_stall_stops_with_exact_account(self):
        result = evaluate(payload(stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("stall:prolonged", result["preservedResults"])
        self.assertIn("queued:raw-0", result["preservedResults"])
        self.assertIn("retained-expected:3", result["preservedResults"])
        self.assertTrue(any("prolonged stall" in item for item in result["openQuestions"]))
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_repeat_cancellation_during_full_pool(self):
        result = evaluate(payload(cancelled=True, stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn("cancelled:full-pool", result["preservedResults"])
        self.assertIn("queued:raw-0", result["preservedResults"])
        self.assertIn("retained-claimed:3", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("full-pool" in item for item in result["reasons"]))

    def test_negative_discard_oldest_fails(self):
        result = evaluate(payload(discardOldest=True, retained=2, indicatorOn=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"stopped"})
        self.assertEqual(result["rejectedClaims"], ["oldest-discarded"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("queued:raw-0", result["preservedResults"])
        self.assertIn("queued:raw-2", result["preservedResults"])
        self.assertIn("indicator:on", result["preservedResults"])
        self.assertIn("retained-expected:3", result["preservedResults"])

    def test_overwritten_samples_fail_and_queue_remains(self):
        result = evaluate(payload(overwrittenIds=["raw-1"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("overwritten-samples", result["rejectedClaims"])
        self.assertIn("queued:raw-1", result["preservedResults"])
        self.assertIn("overwritten:raw-1", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_pool_not_full_does_not_pretend_to_stop(self):
        result = evaluate(payload(queuedIds=["raw-0"], retained=1, capacity=3))
        self.assertEqual(result["decision"], "accepting")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"stopped"})
        self.assertIn("queued:raw-0", result["preservedResults"])
        self.assertIn("retained-expected:1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "capacity": 0},
            {**valid, "stall": "forever"},
            {**valid, "queuedIds": ["raw-0", "raw-0", "raw-1"]},
            {**valid, "overwrittenIds": ["raw-9"]},
            {**valid, "retained": -1},
            {**valid, "cancelled": "yes"},
            {**valid, "indicatorOn": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
