"""TC-P037-05 writer pool saturation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc05", Path(__file__).resolve().parents[1] / "gates" / "p037_tc05.py"
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
        "queuedIds": ["q0", "q1"],
        "queuedTimestamps": ["1000", "2000"],
        "overflowId": "q2",
        "overflowTimestamp": "3000",
        "overwriteOldest": False,
        "indicator": "stopped",
    }
    base.update(overrides)
    return base


class TcP03705(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_short_stall_stops_with_exact_accounting(self):
        result = evaluate(payload(stall="short"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped_visible")
        self.assertEqual(
            result["preservedResults"],
            ["frame:q0@1000", "frame:q1@2000", "overflow:q2@3000"],
        )
        self.assertEqual(result["rejectedClaims"], ["overflow:q2@3000"])
        self.assertIn("retained 2", result["reasons"])
        self.assertEqual(result["openQuestions"], ["short stall stopped at the full pool"])

    def test_prolonged_stall_does_not_overwrite_queued_samples(self):
        result = evaluate(payload(stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped_visible")
        self.assertIn("frame:q0@1000", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["prolonged stall stopped at the full pool"])
        self.assertTrue(any("not overwritten" in item for item in result["reasons"]))

    def test_cancellation_during_full_pool_does_not_resume(self):
        result = evaluate(payload(stall="cancelled_full"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped_visible")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["openQuestions"],
            ["cancellation during the full-pool state did not resume the take"],
        )
        self.assertIn("frame:q0@1000", result["preservedResults"])

    def test_discarding_oldest_to_keep_green_fails(self):
        result = evaluate(payload(overwriteOldest=True, indicator="green", stall="prolonged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stopped_visible"})
        self.assertIn("oldest-discarded-for-indicator", result["rejectedClaims"])
        self.assertIn("frame:q0@1000", result["preservedResults"])
        self.assertIn("overflow:q2@3000", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "queuedIds": ["q0"]},
            {**valid, "indicator": "red"},
            {**valid, "overflowTimestamp": "2000"},
            {**valid, "overwriteOldest": "false"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
