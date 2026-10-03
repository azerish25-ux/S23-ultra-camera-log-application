"""TC-P017-05 source queue exhaustion."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc05", Path(__file__).resolve().parents[1] / "gates" / "p017_tc05.py"
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
        "depth": 2,
        "incomingFrame": "f3",
        "existingFrames": ["f1", "f2"],
        "unbounded": False,
        "hiddenReplacement": False,
    }
    base.update(overrides)
    return base


class TcP01705(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("bounded queue", _MODULE.INTERVENTION)
        self.assertIn("gap evidence", _MODULE.EXPECTED)
        self.assertIn("hidden frame replacement", _MODULE.NEGATIVE)

    def test_capacity_minus_one_enqueues_without_overwrite(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "enqueued")
        self.assertEqual(result["preservedResults"], ["f1", "f2", "f3"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("below capacity" in item for item in result["reasons"]))

    def test_exact_capacity_fails_with_gap_and_keeps_frames(self):
        result = evaluate(
            payload(capacity=3, depth=3, incomingFrame="f4", existingFrames=["f1", "f2", "f3"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["f4"])
        self.assertEqual(result["preservedResults"], ["f1", "f2", "f3"])
        self.assertNotIn("f4", result["preservedResults"])
        self.assertTrue(any("gap evidence f4" in item for item in result["reasons"]))
        self.assertTrue(any("failure policy" in item for item in result["reasons"]))

    def test_first_rejected_item_is_not_written_over_capacity(self):
        result = evaluate(
            payload(capacity=2, depth=2, incomingFrame="frame-reject-1", existingFrames=["a", "b"])
        )
        self.assertEqual(result["decision"], "failed")
        self.assertEqual(result["rejectedClaims"], ["frame-reject-1"])
        self.assertEqual(result["preservedResults"], ["a", "b"])
        self.assertNotIn("frame-reject-1", result["preservedResults"])

    def test_unbounded_queue_is_rejected_and_frames_stay(self):
        result = evaluate(payload(unbounded=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["unbounded-queue"])
        self.assertEqual(result["preservedResults"], ["f1", "f2"])
        self.assertNotIn("f3", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_hidden_replacement_at_capacity_does_not_overwrite(self):
        result = evaluate(
            payload(
                capacity=2,
                depth=2,
                incomingFrame="hidden",
                existingFrames=["keep-1", "keep-2"],
                hiddenReplacement=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["hidden-frame-replacement"])
        self.assertEqual(result["preservedResults"], ["keep-1", "keep-2"])
        self.assertNotIn("hidden", result["preservedResults"])

    def test_both_negatives_are_named(self):
        result = evaluate(payload(unbounded=True, hiddenReplacement=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["unbounded-queue", "hidden-frame-replacement"],
        )
        self.assertEqual(result["preservedResults"], ["f1", "f2"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "capacity": 0},
            {**valid, "capacity": True},
            {**valid, "depth": 4},
            {**valid, "depth": 2, "existingFrames": ["f1"]},
            {**valid, "incomingFrame": "f1"},
            {**valid, "existingFrames": ["f1", "f1"]},
            {**valid, "unbounded": 1},
            {k: v for k, v in valid.items() if k != "capacity"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
