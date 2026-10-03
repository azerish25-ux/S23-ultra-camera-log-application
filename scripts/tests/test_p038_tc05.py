"""TC-P038-05 a full writer pool stops without dropping the oldest frame."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc05", Path(__file__).resolve().parents[1] / "gates" / "p038_tc05.py"
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
        "queuedIds": ["a", "b", "c"],
        "incomingId": "d",
        "stall": "short",
        "cancelDuringFull": False,
        "discardOldest": False,
        "recordingIndicator": True,
    }
    base.update(overrides)
    return base


class TcP03805(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for ident in ("a", "b", "c"):
            self.assertIn(f"queued:{ident}", result["preservedResults"])

    def test_short_stall_stops_with_exact_retention(self):
        result = evaluate(payload(stall="short"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("refused:d", result["preservedResults"])
        self.assertNotIn("queued:d", result["preservedResults"])
        self.assertIn("short-stall", result["openQuestions"])
        self.assertIn("retained:3", result["openQuestions"])
        self.assertTrue(any("3 retained frames" in item for item in result["reasons"]))

    def test_prolonged_stall_also_stops_without_overwrite(self):
        result = evaluate(payload(stall="prolonged", recordingIndicator=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("prolonged-stall", result["openQuestions"])
        self.assertEqual(
            [item for item in result["preservedResults"] if item.startswith("queued:")],
            ["queued:a", "queued:b", "queued:c"],
        )

    def test_cancel_during_full_pool_does_not_resume(self):
        result = evaluate(payload(cancelDuringFull=True, stall="prolonged"))
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("cancelled-during-full", result["openQuestions"])
        self.assertIn("queued:a", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "queued"})

    def test_discarding_the_oldest_to_keep_the_indicator_fails(self):
        result = evaluate(payload(discardOldest=True, recordingIndicator=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["discarded-oldest-raw"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(
            [item for item in result["preservedResults"] if item.startswith("queued:")],
            ["queued:a", "queued:b", "queued:c"],
        )
        self.assertNotIn("queued:d", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stopped"})

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(incomingId="a"))
        with self.assertRaises(ValueError):
            evaluate(payload(stall="forever"))


if __name__ == "__main__":
    unittest.main()
