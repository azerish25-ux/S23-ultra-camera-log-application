"""TC-P037-02 metadata callback reordering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc02", Path(__file__).resolve().parents[1] / "gates" / "p037_tc02.py"
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
        "images": [
            {"id": "i0", "timestampNs": "1000"},
            {"id": "i1", "timestampNs": "2000"},
        ],
        "metadata": [
            {"id": "m1", "timestampNs": "2000"},
            {"id": "m0", "timestampNs": "1000"},
        ],
        "boundNs": 100,
        "association": "exact",
        "repeat": "reordered",
        "delayedMetadataId": None,
    }
    base.update(overrides)
    return base


class TcP03702(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_reordered_exact_timestamps_pair(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "paired")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("image:i0@1000", result["preservedResults"])
        self.assertIn("metadata:m1@2000", result["preservedResults"])
        self.assertTrue(any("paired i0=m0,i1=m1" in item for item in result["reasons"]))
        self.assertIn("callback order was not used as a pairing key", result["openQuestions"])

    def test_duplicate_timestamps_stay_unresolved(self):
        result = evaluate(
            payload(
                metadata=[
                    {"id": "m0", "timestampNs": "1000"},
                    {"id": "m0b", "timestampNs": "1000"},
                ],
                images=[{"id": "i0", "timestampNs": "1000"}],
                repeat="duplicate_timestamps",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "paired"})
        self.assertIn("metadata:m0b@1000", result["preservedResults"])
        self.assertIn("duplicate timestamps left unresolved", result["openQuestions"])

    def test_missing_metadata_stays_unresolved(self):
        result = evaluate(
            payload(
                metadata=[{"id": "m0", "timestampNs": "1000"}],
                repeat="missing_metadata",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("image:i1@2000", result["preservedResults"])
        self.assertIn("missing metadata", result["openQuestions"])
        self.assertTrue(any("i1" in item for item in result["reasons"]))

    def test_delayed_metadata_after_stop_is_not_paired(self):
        result = evaluate(
            payload(
                metadata=[
                    {"id": "m0", "timestampNs": "1000"},
                    {"id": "m1", "timestampNs": "2000"},
                ],
                repeat="delayed_after_stop",
                delayedMetadataId="m1",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("metadata:m1@2000", result["preservedResults"])
        self.assertIn("delayed metadata after stop stayed unresolved", result["openQuestions"])
        self.assertNotIn(result["decision"], {"paired", "qualified", "allowed"})

    def test_nearest_and_latest_association_fail(self):
        nearest = evaluate(payload(association="nearest"))
        latest = evaluate(payload(association="latest"))
        self.assertEqual(nearest["decision"], "rejected")
        self.assertEqual(latest["decision"], "rejected")
        self.assertIn("nearest-time-association", nearest["rejectedClaims"])
        self.assertIn("latest-metadata-association", latest["rejectedClaims"])
        self.assertIn("image:i0@1000", nearest["preservedResults"])
        self.assertIn("metadata:m0@1000", latest["preservedResults"])
        self.assertNotIn(nearest["decision"], {"qualified", "allowed", "paired"})
        self.assertIn(_MODULE.NEGATIVE, nearest["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "association": "fuzzy"},
            {**valid, "boundNs": -1},
            {**valid, "repeat": "reordered", "metadata": valid["images"]},
            {**valid, "delayedMetadataId": "m1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
