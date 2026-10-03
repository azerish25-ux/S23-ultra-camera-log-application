"""TC-P039-05 writer pool saturation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc05", Path(__file__).resolve().parents[1] / "gates" / "p039_tc05.py"
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
        "stall": "short",
        "queuedIds": ["frame-0", "frame-1"],
        "queuedTimestamps": ["10", "20"],
        "overflowId": "frame-2",
        "overflowTimestamp": "30",
        "overwriteOldest": False,
        "indicator": "stopped",
    }
    base.update(overrides)
    return base


class TcP03905(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_short_stall_stops_and_keeps_the_oldest(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped_visible")
        self.assertIn("frame:frame-0@10", result["preservedResults"])
        self.assertIn("frame:frame-1@20", result["preservedResults"])
        self.assertIn("overflow:frame-2@30", result["preservedResults"])
        self.assertIn("short stall stopped at the full pool", result["openQuestions"])

    def test_prolonged_stall_stops_without_overwrite(self):
        result = evaluate(payload(stall="prolonged"))
        self.assertEqual(result["decision"], "stopped_visible")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("frame:frame-0@10", result["preservedResults"])
        self.assertIn("prolonged stall stopped at the full pool", result["openQuestions"])

    def test_cancellation_during_full_pool_does_not_resume(self):
        result = evaluate(payload(stall="cancelled_full"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped_visible")
        self.assertIn("overflow:frame-2@30", result["rejectedClaims"])
        self.assertIn(
            "cancellation during the full-pool state did not resume the take",
            result["openQuestions"],
        )
        self.assertIn("frame:frame-0@10", result["preservedResults"])

    def test_discarding_oldest_for_a_green_indicator_is_rejected(self):
        result = evaluate(payload(overwriteOldest=True, indicator="green"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("oldest-discarded-for-indicator", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("frame:frame-0@10", result["preservedResults"])
        self.assertIn("frame:frame-1@20", result["preservedResults"])
        self.assertIn("overflow:frame-2@30", result["preservedResults"])


if __name__ == "__main__":
    unittest.main()
