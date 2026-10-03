"""TC-P039-02 metadata callback reordering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc02", Path(__file__).resolve().parents[1] / "gates" / "p039_tc02.py"
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
            {"id": "img-a", "timestampNs": "10"},
            {"id": "img-b", "timestampNs": "20"},
        ],
        "metadata": [
            {"id": "meta-b", "timestampNs": "20"},
            {"id": "meta-a", "timestampNs": "10"},
        ],
        "boundNs": 1000,
        "association": "exact",
        "repeat": "reordered",
        "delayedMetadataId": None,
    }
    base.update(overrides)
    return base


class TcP03902(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_reordered_exact_timestamps_pair(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "paired")
        self.assertIn("image:img-a@10", result["preservedResults"])
        self.assertIn("metadata:meta-b@20", result["preservedResults"])
        self.assertIn("callback order was not used as a pairing key", result["openQuestions"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_duplicate_timestamps_stay_unresolved(self):
        result = evaluate(
            payload(
                images=[
                    {"id": "img-a", "timestampNs": "10"},
                    {"id": "img-b", "timestampNs": "10"},
                ],
                metadata=[
                    {"id": "meta-a", "timestampNs": "10"},
                    {"id": "meta-b", "timestampNs": "10"},
                ],
                repeat="duplicate_timestamps",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("image:img-b@10", result["preservedResults"])
        self.assertIn("duplicate timestamps left unresolved", result["openQuestions"])

    def test_missing_metadata_stays_unresolved(self):
        result = evaluate(
            payload(
                metadata=[{"id": "meta-a", "timestampNs": "10"}],
                repeat="missing_metadata",
            )
        )
        self.assertEqual(result["decision"], "unresolved")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("image:img-b@20", result["preservedResults"])
        self.assertIn("missing metadata", result["openQuestions"])

    def test_delayed_metadata_after_stop_stays_unresolved(self):
        result = evaluate(
            payload(
                images=[{"id": "img-a", "timestampNs": "10"}],
                metadata=[{"id": "meta-a", "timestampNs": "10"}],
                repeat="delayed_after_stop",
                delayedMetadataId="meta-a",
            )
        )
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("metadata:meta-a@10", result["preservedResults"])
        self.assertIn("delayed metadata after stop stayed unresolved", result["openQuestions"])

    def test_nearest_time_negative_is_rejected(self):
        result = evaluate(payload(association="nearest"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("nearest-time-association", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("image:img-a@10", result["preservedResults"])

    def test_latest_metadata_negative_is_rejected(self):
        result = evaluate(payload(association="latest"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("latest-metadata-association", result["rejectedClaims"])
        self.assertIn("metadata:meta-a@10", result["preservedResults"])


if __name__ == "__main__":
    unittest.main()
