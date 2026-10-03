"""TC-P034-05 writer pool saturation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc05", Path(__file__).resolve().parents[1] / "gates" / "p034_tc05.py"
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
FULL = ["a", "b", "c"]


def payload(**overrides):
    base = {
        "capacity": 3,
        "queuedIds": list(FULL),
        "stall": "short",
        "cancelDuringFull": False,
        "discardOldest": False,
    }
    base.update(overrides)
    return base


class TcP03405(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for item in FULL:
            self.assertIn(f"frame:{item}", result["preservedResults"])

    def test_module_encodes_case_text(self):
        self.assertIn("preallocated source-copy capacity", _MODULE.INTERVENTION)
        self.assertIn("exact retained-frame accounting", _MODULE.EXPECTED)
        self.assertIn("oldest RAW record", _MODULE.NEGATIVE)

    def test_short_stall_stops_and_keeps_every_frame(self):
        result = evaluate(payload(stall="short"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("retained:3", result["preservedResults"])
        self.assertIn("stall:short", result["preservedResults"])
        self.assertIn("visible stop", result["openQuestions"])
        self.assertIn("stall short", " ".join(result["reasons"]))

    def test_prolonged_stall_stops_without_overwriting(self):
        result = evaluate(payload(stall="prolonged"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("stall:prolonged", result["preservedResults"])
        self.assertEqual(
            [item for item in result["preservedResults"] if item.startswith("frame:")],
            ["frame:a", "frame:b", "frame:c"],
        )

    def test_cancel_during_full_pool_keeps_frames(self):
        result = evaluate(payload(cancelDuringFull=True, stall="prolonged"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "cancelled")
        self.assertIn("frame:a", result["preservedResults"])
        self.assertIn("frame:c", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["cancelled during full pool"])
        self.assertNotEqual(result["decision"], "stopped")

    def test_negative_discard_oldest_fails_and_keeps_ids(self):
        result = evaluate(payload(discardOldest=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stopped"})
        self.assertEqual(result["rejectedClaims"], ["discard-oldest"])
        self.assertIn("frame:a", result["preservedResults"])
        self.assertIn("retained:3", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("recording indicator is not retained-frame accounting", result["openQuestions"])

    def test_below_capacity_is_not_a_stop(self):
        result = evaluate(payload(queuedIds=["a", "b"], stall="short"))
        self.assertEqual(result["decision"], "accepting")
        self.assertIn("frame:a", result["preservedResults"])
        self.assertIn("frame:b", result["preservedResults"])
        self.assertNotIn("frame:c", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(queuedIds=["a", "b"], cancelDuringFull=True))
        with self.assertRaises(ValueError):
            evaluate(payload(queuedIds=["a", "a", "b"]))


if __name__ == "__main__":
    unittest.main()
