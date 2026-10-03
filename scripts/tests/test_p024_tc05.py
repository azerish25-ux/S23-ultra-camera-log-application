"""TC-P024-05 source queue exhaustion stops with gap evidence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p024_tc05", Path(__file__).resolve().parents[1] / "gates" / "p024_tc05.py"
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
        "position": "capacity_minus_one",
        "queuedIds": ["f0", "f1"],
        "rejectedItemId": None,
        "unbounded": False,
        "hiddenReplacement": False,
        "stopOrFail": False,
        "gapEvidence": False,
    }
    base.update(overrides)
    return base


class TcP02405(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P024-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("explicitly bounded queue", _MODULE.INTERVENTION)
        self.assertIn("gap evidence", _MODULE.EXPECTED)
        self.assertIn("unbounded queue", _MODULE.NEGATIVE)
        self.assertEqual(
            _MODULE.POSITIONS,
            ("capacity_minus_one", "exact_capacity", "first_rejected"),
        )

    def test_capacity_minus_one_accepts_and_keeps_frames(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "accepted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["capacity:3", "frame:f0", "frame:f1"],
        )
        self.assertTrue(any("capacity_minus_one" in item for item in result["reasons"]))

    def test_exact_capacity_retains_every_queued_frame(self):
        result = evaluate(
            payload(position="exact_capacity", queuedIds=["f0", "f1", "f2"], capacity=3)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "at_capacity")
        self.assertEqual(
            result["preservedResults"],
            ["capacity:3", "frame:f0", "frame:f1", "frame:f2"],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(any("exact_capacity" in item for item in result["reasons"]))

    def test_first_rejected_item_stops_with_gap_evidence(self):
        result = evaluate(
            payload(
                position="first_rejected",
                queuedIds=["f0", "f1", "f2"],
                rejectedItemId="f3",
                stopOrFail=True,
                gapEvidence=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f2", result["preservedResults"])
        self.assertIn("gap:f3", result["preservedResults"])
        self.assertIn("gap evidence recorded; source frames were not replaced", result["openQuestions"])
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_unbounded_queue_is_rejected_and_frames_remain(self):
        result = evaluate(payload(unbounded=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "accepted"})
        self.assertIn("unbounded-queue", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["capacity:3", "frame:f0", "frame:f1"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_hidden_replacement_at_exact_capacity_is_rejected(self):
        result = evaluate(
            payload(
                position="exact_capacity",
                queuedIds=["f0", "f1", "f2"],
                hiddenReplacement=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-frame-replacement", result["rejectedClaims"])
        self.assertIn("frame:f0", result["preservedResults"])
        self.assertIn("frame:f2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "at_capacity"})

    def test_first_rejected_without_gap_evidence_fails(self):
        result = evaluate(
            payload(
                position="first_rejected",
                queuedIds=["f0", "f1", "f2"],
                rejectedItemId="f3",
                stopOrFail=True,
                gapEvidence=False,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-gap-evidence", result["rejectedClaims"])
        self.assertIn("gap:f3", result["preservedResults"])
        self.assertIn("frame:f1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "position": "overflow"},
            {**valid, "capacity": 0},
            {**valid, "queuedIds": ["f0"]},
            {**valid, "queuedIds": ["f0", "f0"]},
            {**valid, "rejectedItemId": "f9"},
            {**valid, "unbounded": 1},
            {key: value for key, value in valid.items() if key != "position"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
