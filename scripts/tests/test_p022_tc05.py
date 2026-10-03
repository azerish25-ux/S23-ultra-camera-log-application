"""TC-P022-05 a bounded source queue stops with gap evidence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc05", Path(__file__).resolve().parents[1] / "gates" / "p022_tc05.py"
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
_HASH = "cm-queue"


def payload(**overrides):
    base = {
        "capacity": 4,
        "occupancy": 3,
        "policy": "stop_with_gap",
        "gapEvidence": None,
        "incomingFrame": "f-next",
        "retainedFrames": ["f0", "f1", "f2"],
        "cleanMasterHash": _HASH,
    }
    base.update(overrides)
    return base


class TcP02205(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("bounded queue", _MODULE.INTERVENTION)
        self.assertIn("gap evidence", _MODULE.EXPECTED)
        self.assertIn("hidden frame replacement", _MODULE.NEGATIVE)

    def test_capacity_minus_one_fills_to_exact_capacity(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "at_capacity")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["f0", "f1", "f2", "f-next", _HASH])
        self.assertTrue(any("exact capacity" in item for item in result["reasons"]))

    def test_below_capacity_minus_one_queues_the_frame(self):
        result = evaluate(
            payload(occupancy=2, retainedFrames=["f0", "f1"], incomingFrame="f2")
        )
        self.assertEqual(result["decision"], "queued")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["f0", "f1", "f2", _HASH])

    def test_first_rejected_item_stops_with_gap_evidence(self):
        result = evaluate(
            payload(
                occupancy=4,
                retainedFrames=["f0", "f1", "f2", "f3"],
                incomingFrame="f-rejected",
                gapEvidence="gap-after-f3",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["preservedResults"],
            ["f0", "f1", "f2", "f3", "f-rejected", _HASH],
        )
        self.assertTrue(any("gap-after-f3" in item for item in result["reasons"]))
        self.assertTrue(any("first item past capacity" in item for item in result["reasons"]))
        self.assertIn("source gap recorded; capture did not continue silently", result["openQuestions"])

    def test_unbounded_queue_is_rejected_and_keeps_frames(self):
        result = evaluate(payload(policy="unbounded"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "queued", "at_capacity"})
        self.assertEqual(result["rejectedClaims"], ["unbounded-queue"])
        self.assertEqual(result["preservedResults"], ["f0", "f1", "f2", "f-next", _HASH])

    def test_hidden_replacement_does_not_drop_the_oldest_frame(self):
        result = evaluate(payload(policy="replace_hidden", occupancy=4, retainedFrames=["f0", "f1", "f2", "f3"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["hidden-frame-replacement"])
        self.assertEqual(result["preservedResults"][0], "f0")
        self.assertIn("f3", result["preservedResults"])
        self.assertIn(_HASH, result["preservedResults"])
        self.assertTrue(any("not overwritten" in item for item in result["reasons"]))

    def test_stop_without_gap_evidence_is_rejected(self):
        result = evaluate(
            payload(occupancy=4, retainedFrames=["f0", "f1", "f2", "f3"], gapEvidence=None)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-gap-evidence", result["rejectedClaims"])
        self.assertIn("f0", result["preservedResults"])
        self.assertIn(_HASH, result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "capacity": 0},
            {**valid, "occupancy": 5, "retainedFrames": ["f0", "f1", "f2", "f3", "f4"]},
            {**valid, "policy": "drop"},
            {**valid, "gapEvidence": "too-soon"},
            {**valid, "incomingFrame": "f0"},
            {**valid, "capacity": True},
            {k: v for k, v in valid.items() if k != "policy"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
