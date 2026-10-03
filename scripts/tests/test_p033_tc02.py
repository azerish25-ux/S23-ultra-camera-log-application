"""TC-P033-02 metadata callback reordering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc02", Path(__file__).resolve().parents[1] / "gates" / "p033_tc02.py"
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
_FORBIDDEN = {"qualified", "allowed"}


def payload(**overrides):
    base = {
        "imageIds": ["i0", "i1"],
        "imageTimestamps": ["1000", "2000"],
        "metadataIds": ["m1", "m0"],
        "metadataTimestamps": ["2000", "1000"],
        "metadataDelaysNs": [0, 4],
        "metadataAfterStop": [False, False],
        "association": "exact",
        "boundNs": 10,
        "stopped": False,
        "inventory": ["callback-order", "sensor-clock"],
    }
    base.update(overrides)
    return base


class TcP03302(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-02")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])

    def test_reordered_exact_match_pairs_inside_the_bound(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "paired")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("pair:i0->m0", result["preservedResults"])
        self.assertIn("pair:i1->m1", result["preservedResults"])
        self.assertIn("callback-order", result["preservedResults"])
        self.assertNotIn("unresolved:i0", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn("exact match", _MODULE.INTERVENTION)

    def test_repeat_duplicate_timestamps_stay_unresolved(self):
        result = evaluate(
            payload(
                imageTimestamps=["1000", "1000"],
                metadataIds=["m0"],
                metadataTimestamps=["1000"],
                metadataDelaysNs=[0],
                metadataAfterStop=[False],
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"paired"})
        self.assertEqual(result["rejectedClaims"], ["ambiguous-timestamp"])
        self.assertIn("unresolved:i0", result["preservedResults"])
        self.assertIn("unresolved:i1", result["preservedResults"])
        self.assertNotIn("pair:i0->m0", result["preservedResults"])
        self.assertIn("image:i0", result["preservedResults"])
        self.assertIn("sensor-clock", result["preservedResults"])

    def test_repeat_missing_metadata_stays_unresolved(self):
        result = evaluate(
            payload(
                imageIds=["i0"],
                imageTimestamps=["1000"],
                metadataIds=["m9"],
                metadataTimestamps=["9000"],
                metadataDelaysNs=[0],
                metadataAfterStop=[False],
            )
        )
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("missing-metadata", result["rejectedClaims"])
        self.assertIn("unresolved:i0", result["preservedResults"])
        self.assertIn("metadata:m9", result["preservedResults"])
        self.assertIn("callback-order", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_repeat_delayed_metadata_after_stop(self):
        result = evaluate(
            payload(
                metadataAfterStop=[False, True],
                metadataDelaysNs=[0, 0],
                stopped=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"paired"})
        self.assertEqual(result["rejectedClaims"], ["delayed-after-stop"])
        self.assertIn("pair:i1->m1", result["preservedResults"])
        self.assertIn("unresolved:i0", result["preservedResults"])
        self.assertIn("metadata:m0", result["preservedResults"])
        self.assertIn("sensor-clock", result["preservedResults"])

    def test_negative_nearest_time_fails(self):
        result = evaluate(payload(association="nearest"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"paired"})
        self.assertEqual(result["rejectedClaims"], ["nearest-time"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("image:i0", result["preservedResults"])
        self.assertIn("metadata:m0", result["preservedResults"])
        self.assertNotIn("pair:i0->m0", result["preservedResults"])
        self.assertIn("callback-order", result["preservedResults"])

    def test_negative_latest_metadata_fails(self):
        result = evaluate(payload(association="latest", stopped=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["latest-metadata"])
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn("image:i1", result["preservedResults"])
        self.assertIn("metadata:m1", result["preservedResults"])
        self.assertFalse(any(item.startswith("pair:") for item in result["preservedResults"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "association": "fuzzy"},
            {**valid, "boundNs": -1},
            {**valid, "imageTimestamps": ["1000"]},
            {**valid, "metadataDelaysNs": [0, True]},
            {**valid, "metadataAfterStop": [False, 0]},
            {**valid, "stopped": "yes"},
            {**valid, "imageIds": ["m0", "i1"]},
            {**valid, "inventory": []},
            {**valid, "imageTimestamps": ["0100", "2000"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
