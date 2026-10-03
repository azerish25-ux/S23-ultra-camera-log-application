"""TC-P020-05 host checks. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc05", Path(__file__).resolve().parents[1] / "gates" / "p020_tc05.py"
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
_INVENTORY = _MODULE.WB_INVENTORY


def _contract(test, result):
    test.assertEqual(tuple(result), _KEYS)
    test.assertEqual(result["caseId"], "TC-P020-05")
    test.assertNotIn(result["decision"], {"qualified", "allowed"})
    test.assertIsInstance(result["reasons"], list)
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
    for key in ("rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) for item in result[key]))


def _inventory(test, result):
    for item in _INVENTORY:
        test.assertIn(item, result["preservedResults"])


def payload(**overrides):
    base = {
        "capacity": 2,
        "queued": 1,
        "incoming": "frame-c",
        "bounded": True,
        "replacesHidden": False,
        "retainedFrames": ["frame-a", "frame-b"],
    }
    base.update(overrides)
    return base


class TcP02005(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertIn("bounded queue", _MODULE.INTERVENTION)
        self.assertIn("gap evidence", _MODULE.EXPECTED)
        self.assertIn("hidden frame replacement", _MODULE.NEGATIVE)
        self.assertEqual(_MODULE.REPEATS, ("capacity_minus_one", "exact_capacity", "first_rejected_item"))

    def test_capacity_minus_one_enqueues_without_dropping_frames(self):
        result = evaluate(payload())
        _contract(self, result)
        self.assertEqual(result["decision"], "enqueued")
        self.assertIn("frame:frame-a", result["preservedResults"])
        self.assertIn("frame:frame-b", result["preservedResults"])
        self.assertIn("frame:frame-c", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("capacity_minus_one" in item for item in result["reasons"]))

    def test_exact_capacity_stops_with_gap_evidence(self):
        result = evaluate(payload(queued=2, incoming="frame-d"))
        _contract(self, result)
        self.assertEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("frame-d", result["rejectedClaims"])
        self.assertIn("gap-evidence:frame-d", result["preservedResults"])
        self.assertNotIn("frame:frame-d", result["preservedResults"])
        self.assertIn("frame:frame-a", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("exact_capacity" in item for item in result["reasons"]))
        self.assertTrue(any("first_rejected_item" in item for item in result["reasons"]))

    def test_unbounded_queue_is_rejected_and_frames_stay(self):
        result = evaluate(payload(bounded=False, incoming="frame-x"))
        _contract(self, result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "enqueued"})
        self.assertIn("unbounded-queue", result["rejectedClaims"])
        self.assertNotIn("frame:frame-x", result["preservedResults"])
        self.assertIn("frame:frame-a", result["preservedResults"])
        _inventory(self, result)

    def test_hidden_replacement_is_rejected(self):
        result = evaluate(payload(queued=2, replacesHidden=True, incoming="frame-hidden"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-frame-replacement", result["rejectedClaims"])
        self.assertNotIn("frame:frame-hidden", result["preservedResults"])
        _inventory(self, result)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [None, {**valid, "queued": 3}, {**valid, "incoming": "frame-a"}, {**valid, "capacity": 0}]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
