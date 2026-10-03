"""TC-P034-02 metadata callback reordering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc02", Path(__file__).resolve().parents[1] / "gates" / "p034_tc02.py"
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


def event(kind, ident, stamp):
    return {"kind": kind, "id": ident, "ts": stamp}


def payload(events, association="exact", pending_limit=4):
    return {"association": association, "pendingLimit": pending_limit, "events": events}


REORDER = [
    event("image", "early", "1000"),
    event("metadata", "late", "2000"),
    event("image", "absent", "3000"),
    event("image", "late", "2000"),
    event("metadata", "early", "1000"),
    event("stop", "stop", "0"),
]


class TcP03402(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("callback order", _MODULE.INTERVENTION)
        self.assertIn("matching sensor timestamps", _MODULE.EXPECTED)
        self.assertIn("Nearest-time or latest-metadata", _MODULE.NEGATIVE)

    def test_reordered_callbacks_pair_only_exact_timestamps(self):
        result = evaluate(payload(REORDER))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "gapped")
        self.assertIn("exact:late@2000", result["preservedResults"])
        self.assertIn("exact:early@1000", result["preservedResults"])
        self.assertIn("gap:absent@3000", result["preservedResults"])
        self.assertIn("image:absent@3000", result["preservedResults"])
        self.assertNotIn("exact:absent@3000", result["preservedResults"])
        self.assertNotIn("exact:absent@2000", result["preservedResults"])
        self.assertIn("missing-metadata:absent", result["openQuestions"])

    def test_duplicate_timestamps_keep_both_ids(self):
        events = [
            event("metadata", "meta", "1000"),
            event("image", "keep", "1000"),
            event("image", "dup", "1000"),
            event("stop", "stop", "0"),
        ]
        result = evaluate(payload(events))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-timestamp:1000", result["rejectedClaims"])
        self.assertIn("exact:keep@1000", result["preservedResults"])
        self.assertIn("image:dup@1000", result["preservedResults"])
        self.assertIn("duplicate:image:dup@1000", result["preservedResults"])

    def test_missing_metadata_stays_unresolved(self):
        events = [
            event("image", "only", "5000"),
            event("stop", "stop", "0"),
        ]
        result = evaluate(payload(events))
        self.assertEqual(result["decision"], "gapped")
        self.assertIn("gap:only@5000", result["preservedResults"])
        self.assertIn("image:only@5000", result["preservedResults"])
        self.assertFalse(any(item.startswith("exact:") for item in result["preservedResults"]))
        self.assertIn("missing-metadata:only", result["openQuestions"])

    def test_delayed_metadata_after_stop_does_not_pair(self):
        events = [
            event("image", "held", "1000"),
            event("stop", "stop", "0"),
            event("metadata", "heldMeta", "1000"),
        ]
        result = evaluate(payload(events))
        self.assertEqual(result["decision"], "gapped")
        self.assertIn("gap:held@1000", result["preservedResults"])
        self.assertIn("after-stop:metadata:heldMeta@1000", result["preservedResults"])
        self.assertIn("metadata-after-stop:heldMeta", result["openQuestions"])
        self.assertNotIn("exact:held@1000", result["preservedResults"])
        self.assertNotIn("exact:heldMeta@1000", result["preservedResults"])

    def test_negative_nearest_and_latest_fail(self):
        nearest = evaluate(payload(
            [event("image", "frame", "1000"), event("metadata", "near", "1001"), event("stop", "stop", "0")],
            association="nearest",
        ))
        self.assert_contract(nearest)
        self.assertEqual(nearest["decision"], "rejected")
        self.assertIn("nearest-time", nearest["rejectedClaims"])
        self.assertIn("image:frame@1000", nearest["preservedResults"])
        self.assertIn("metadata:near@1001", nearest["preservedResults"])
        self.assertFalse(any(item.startswith("exact:") for item in nearest["preservedResults"]))
        self.assertIn(_MODULE.NEGATIVE, nearest["reasons"])
        latest = evaluate(payload(REORDER, association="latest"))
        self.assertEqual(latest["decision"], "rejected")
        self.assertNotIn(latest["decision"], {"qualified", "allowed", "gapped"})
        self.assertIn("latest-metadata", latest["rejectedClaims"])
        self.assertIn("image:absent@3000", latest["preservedResults"])
        self.assertFalse(any(item.startswith("exact:") for item in latest["preservedResults"]))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload([]))
        with self.assertRaises(ValueError):
            evaluate({"association": "exact", "pendingLimit": 1, "events": REORDER, "extra": 1})


if __name__ == "__main__":
    unittest.main()
