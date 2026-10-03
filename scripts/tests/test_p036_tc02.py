"""TC-P036-02 metadata callback reordering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc02", Path(__file__).resolve().parents[1] / "gates" / "p036_tc02.py"
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
        "imageTimestampNs": "1000",
        "metadataTimestampNs": "1000",
        "callbackOrder": "image_before_metadata",
        "policyBoundNs": 50,
        "delayNs": 10,
        "association": "exact_timestamp",
        "duplicateTimestamp": False,
        "missingMetadata": False,
        "delayedAfterStop": False,
    }
    base.update(overrides)
    return base


class TcP03602(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_delayed_exact_match_inside_bound_pairs(self):
        result = evaluate(payload(callbackOrder="metadata_before_image"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "paired")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("image:1000", result["preservedResults"])
        self.assertIn("metadata:1000", result["preservedResults"])
        self.assertIn("order:metadata_before_image", result["preservedResults"])
        self.assertIn("delay:10", result["preservedResults"])

    def test_duplicate_timestamps_stay_unresolved(self):
        result = evaluate(payload(duplicateTimestamp=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "paired"})
        self.assertIn("image:1000", result["preservedResults"])
        self.assertIn("metadata:1000", result["preservedResults"])
        self.assertIn("duplicate timestamp", result["openQuestions"])

    def test_missing_metadata_stays_unresolved(self):
        result = evaluate(payload(missingMetadata=True, metadataTimestampNs=None))
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("metadata:missing", result["preservedResults"])
        self.assertIn("image:1000", result["preservedResults"])
        self.assertIn("metadata missing", result["openQuestions"])

    def test_delayed_metadata_after_stop_stays_unresolved(self):
        result = evaluate(payload(delayedAfterStop=True, delayNs=40))
        self.assertEqual(result["decision"], "unresolved")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "paired"})
        self.assertIn("delayed after stop", result["openQuestions"])
        self.assertIn("metadata:1000", result["preservedResults"])
        self.assertIn("bound:50", result["preservedResults"])

    def test_negative_nearest_time_fails(self):
        result = evaluate(payload(association="nearest_time", metadataTimestampNs="1004"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "paired"})
        self.assertIn("nearest-time", result["rejectedClaims"])
        self.assertIn("image:1000", result["preservedResults"])
        self.assertIn("metadata:1004", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_negative_latest_metadata_fails(self):
        result = evaluate(payload(association="latest_metadata"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("latest-metadata", result["rejectedClaims"])
        self.assertIn("image:1000", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_outside_bound_is_unresolved(self):
        result = evaluate(payload(delayNs=80))
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("outside bounded policy", result["openQuestions"])
        self.assertIn("delay:80", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "policyBoundNs": 0},
            {**valid, "association": "fuzzy"},
            {**valid, "missingMetadata": True},
            {**valid, "imageTimestampNs": 1000},
            {**valid, "delayNs": -1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
