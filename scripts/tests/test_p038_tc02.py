"""TC-P038-02 exact timestamp pairing only."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc02", Path(__file__).resolve().parents[1] / "gates" / "p038_tc02.py"
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


def frame(ident, stamp, order):
    return {"id": ident, "sensorTimestamp": stamp, "order": order}


def meta(ident, stamp, order, after_stop=False):
    return {
        "id": ident,
        "sensorTimestamp": stamp,
        "order": order,
        "afterStop": after_stop,
    }


def payload(**overrides):
    base = {
        "frames": [frame("f1", "1000", 1), frame("f2", "2000", 2)],
        "metadata": [meta("m-late", "1000", 4), meta("m2", "2000", 3)],
        "bound": 5,
        "association": "exact",
    }
    base.update(overrides)
    return base


class TcP03802(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("frame:f1@1000", result["preservedResults"])

    def test_delayed_exact_match_inside_the_bound_pairs(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "paired")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("pair:f1>m-late", result["preservedResults"])
        self.assertIn("pair:f2>m2", result["preservedResults"])
        self.assertIn("metadata:m-late@1000", result["preservedResults"])

    def test_nearest_time_association_fails(self):
        result = evaluate(payload(association="nearest"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["nearest-time"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "paired"})
        self.assertFalse(any(item.startswith("pair:") for item in result["preservedResults"]))
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_latest_metadata_association_fails(self):
        result = evaluate(payload(association="latest"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["latest-metadata"])
        self.assertIn("frame:f2@2000", result["preservedResults"])

    def test_duplicate_timestamps_stay_unresolved(self):
        result = evaluate(
            payload(
                frames=[frame("f1", "1000", 1)],
                metadata=[meta("m1", "1000", 2), meta("m2", "1000", 3)],
            )
        )
        self.assertEqual(result["decision"], "unresolved")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "paired"})
        self.assertEqual(result["openQuestions"], ["unresolved:f1"])
        self.assertIn("metadata:m1@1000", result["preservedResults"])
        self.assertIn("metadata:m2@1000", result["preservedResults"])
        self.assertFalse(any(item.startswith("pair:") for item in result["preservedResults"]))

    def test_missing_metadata_and_delay_after_stop_stay_unresolved(self):
        missing = evaluate(
            payload(frames=[frame("f1", "1000", 1), frame("f2", "2000", 2)], metadata=[])
        )
        self.assertEqual(missing["decision"], "unresolved")
        self.assertIn("frame:f2@2000", missing["preservedResults"])
        self.assertEqual(missing["openQuestions"], ["unresolved:f1", "unresolved:f2"])
        delayed = evaluate(
            payload(
                frames=[frame("f1", "1000", 1)],
                metadata=[meta("m1", "1000", 2, after_stop=True)],
            )
        )
        self.assertEqual(delayed["decision"], "unresolved")
        self.assertIn("metadata:m1@1000", delayed["preservedResults"])
        self.assertNotIn("pair:f1>m1", delayed["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        with self.assertRaises(ValueError):
            evaluate({**valid, "association": "first"})
        with self.assertRaises(ValueError):
            evaluate(None)


if __name__ == "__main__":
    unittest.main()
