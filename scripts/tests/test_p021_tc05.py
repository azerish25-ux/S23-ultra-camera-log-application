"""TC-P021-05 source queue exhaustion."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc05", Path(__file__).resolve().parents[1] / "gates" / "p021_tc05.py"
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
        "queued": 1,
        "incoming": "f1",
        "bounded": True,
        "replacesHidden": False,
        "retainedFrames": ["f0"],
    }
    base.update(overrides)
    return base


class TcP02105(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _MODULE.FOCUS_INVENTORY:
            self.assertIn(token, result["preservedResults"])

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("explicitly bounded queue", _MODULE.INTERVENTION)
        self.assertIn("never silently overwrite source frames", _MODULE.EXPECTED)
        self.assertIn("unbounded queue or hidden frame replacement", _MODULE.NEGATIVE)
        self.assertEqual(
            _MODULE.REPEATS,
            ("capacity_minus_one", "exact_capacity", "first_rejected_item"),
        )

    def test_repeat_capacity_minus_one_enqueues(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "enqueued")
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])
        self.assertLess(
            result["preservedResults"].index("frame:f0"),
            result["preservedResults"].index("frame:f1"),
        )
        self.assertTrue(any("capacity_minus_one" in item for item in result["reasons"]))

    def test_repeat_exact_capacity_stops_with_gap_evidence(self):
        result = evaluate(payload(queued=2, incoming="f2", retainedFrames=["f0", "f1"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])
        self.assertNotIn("frame:f2", result["preservedResults"])
        self.assertIn("gap-evidence:f2", result["preservedResults"])
        self.assertIn("f2", result["rejectedClaims"])
        self.assertTrue(any("exact_capacity" in item for item in result["reasons"]))
        self.assertIn("physical.distance:unknown", result["preservedResults"])

    def test_repeat_first_rejected_item_is_not_written_over_frames(self):
        result = evaluate(
            payload(queued=2, incoming="rejected-item", retainedFrames=["f0", "f1"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], ["rejected-item"])
        self.assertIn("gap-evidence:rejected-item", result["preservedResults"])
        self.assertNotIn("frame:rejected-item", result["preservedResults"])
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])
        self.assertTrue(any("first_rejected_item" in item for item in result["reasons"]))

    def test_negative_unbounded_queue_does_not_overwrite(self):
        result = evaluate(
            payload(bounded=False, queued=2, incoming="f9", retainedFrames=["f0", "f1"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "enqueued", "stopped"})
        self.assertIn("unbounded-queue", result["rejectedClaims"])
        self.assertNotIn("frame:f9", result["preservedResults"])
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])

    def test_negative_hidden_replacement_keeps_retained_frames(self):
        result = evaluate(payload(replacesHidden=True, incoming="secret"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("hidden-frame-replacement", result["rejectedClaims"])
        self.assertNotIn("frame:secret", result["preservedResults"])
        self.assertIn("virtual.subject:face", result["preservedResults"])
        self.assertIn("frame:f0", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "capacity": 0},
            {**valid, "queued": 3},
            {**valid, "queued": True},
            {**valid, "incoming": "f0"},
            {**valid, "bounded": "yes"},
            {**valid, "retainedFrames": ["f0", "f0"]},
            {**valid, "queued": 0, "retainedFrames": ["f0"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
