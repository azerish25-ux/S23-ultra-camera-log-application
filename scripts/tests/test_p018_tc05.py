"""TC-P018-05 source queue exhaustion."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p018_tc05", Path(__file__).resolve().parents[1] / "gates" / "p018_tc05.py"
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
        "capacity": 3,
        "unbounded": False,
        "hiddenReplacement": False,
        "depth": 2,
        "incoming": "frame-3",
        "frames": ["frame-1", "frame-2"],
    }
    base.update(overrides)
    return base


class TcP01805(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P018-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_contract(self):
        self.assertIn("bounded queue reaches capacity", _MODULE.INTERVENTION)
        self.assertIn("gap evidence", _MODULE.EXPECTED)
        self.assertIn("hidden frame replacement", _MODULE.NEGATIVE)
        self.assertIn("capacity minus one", _MODULE.REPEAT)
        self.assertIn("first rejected item", _MODULE.REPEAT)

    def test_capacity_minus_one_admits_without_overwrite(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "enqueued")
        self.assertEqual(result["preservedResults"], ["frame-1", "frame-2", "frame-3"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_exact_capacity_stops_and_records_the_gap(self):
        result = evaluate(
            payload(depth=3, incoming="frame-4", frames=["frame-1", "frame-2", "frame-3"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["preservedResults"], ["frame-1", "frame-2", "frame-3"])
        self.assertNotIn("frame-4", result["preservedResults"])
        self.assertIn("rejected:frame-4", result["rejectedClaims"])
        self.assertTrue(any("gap:frame-4" in item for item in result["reasons"]))

    def test_first_rejected_item_is_not_written_over_the_held_frame(self):
        result = evaluate(payload(capacity=1, depth=1, incoming="frame-b", frames=["frame-a"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["preservedResults"], ["frame-a"])
        self.assertEqual(result["rejectedClaims"], ["rejected:frame-b"])
        self.assertTrue(any("gap:frame-b" in item for item in result["reasons"]))

    def test_unbounded_queue_and_hidden_replacement_are_rejected(self):
        unbounded = evaluate(
            payload(unbounded=True, capacity=None, depth=1, frames=["frame-1"], incoming="frame-2")
        )
        self.assertEqual(unbounded["decision"], "rejected")
        self.assertNotIn(unbounded["decision"], {"qualified", "allowed"})
        self.assertIn("unbounded-queue", unbounded["rejectedClaims"])
        self.assertEqual(unbounded["preservedResults"], ["frame-1"])

        hidden = evaluate(
            payload(
                hiddenReplacement=True,
                depth=2,
                frames=["frame-1", "frame-2"],
                incoming="frame-2",
            )
        )
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("hidden-frame-replacement", hidden["rejectedClaims"])
        self.assertEqual(hidden["preservedResults"], ["frame-1", "frame-2"])
        self.assertNotIn(hidden["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "capacity": 0},
            {**valid, "capacity": True},
            {**valid, "depth": 1},
            {**valid, "frames": ["frame-1", "frame-1"]},
            {**valid, "incoming": "frame-1"},
            {**valid, "unbounded": "false"},
            {**valid, "depth": 4, "frames": ["a", "b", "c", "d"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
