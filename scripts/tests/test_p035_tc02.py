"""TC-P035-02 metadata callback reordering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc02", Path(__file__).resolve().parents[1] / "gates" / "p035_tc02.py"
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


def image(ident="a", stamp="100"):
    return {"id": ident, "sensorTimestamp": stamp}


def meta(ident="m", stamp="100"):
    return {"id": ident, "sensorTimestamp": stamp}


def payload(**overrides):
    base = {
        "images": [image()],
        "metadata": [meta()],
        "order": ["image:a", "metadata:m"],
        "association": "exact",
    }
    base.update(overrides)
    return base


class TcP03502(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_delayed_exact_match_pairs(self):
        result = evaluate(payload(order=["image:a", "metadata:m"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "paired")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("pair:a=m", result["preservedResults"])
        self.assertIn("image:a@100", result["preservedResults"])
        self.assertIn("metadata:m@100", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_duplicate_timestamps(self):
        result = evaluate(
            payload(
                metadata=[meta("m1", "100"), meta("m2", "100")],
                order=["metadata:m1", "image:a", "metadata:m2"],
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["duplicate-timestamp"])
        self.assertIn("metadata:m1@100", result["preservedResults"])
        self.assertIn("metadata:m2@100", result["preservedResults"])
        self.assertFalse(any(item.startswith("pair:") for item in result["preservedResults"]))

    def test_repeat_missing_metadata_stays_unresolved(self):
        result = evaluate(payload(metadata=[], order=["image:a"]))
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("unresolved:a", result["preservedResults"])
        self.assertIn("image:a@100", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "paired"})

    def test_repeat_delayed_metadata_after_stop(self):
        result = evaluate(payload(order=["image:a", "stop", "metadata:m"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "unresolved")
        self.assertIn("unresolved:a", result["preservedResults"])
        self.assertIn("metadata:m@100", result["preservedResults"])
        self.assertNotIn("pair:a=m", result["preservedResults"])
        self.assertIn("delayed metadata after stop", result["openQuestions"])

    def test_negative_nearest_and_latest_fail(self):
        nearest = evaluate(payload(association="nearest"))
        self.assertEqual(nearest["decision"], "rejected")
        self.assertEqual(nearest["rejectedClaims"], ["nearest-time"])
        self.assertIn("image:a@100", nearest["preservedResults"])
        self.assertNotIn("pair:a=m", nearest["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, nearest["reasons"])
        latest = evaluate(payload(association="latest", order=["metadata:m", "image:a"]))
        self.assertEqual(latest["decision"], "rejected")
        self.assertEqual(latest["rejectedClaims"], ["latest-metadata"])
        self.assertIn("metadata:m@100", latest["preservedResults"])
        self.assertNotIn(latest["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {key: value for key, value in valid.items() if key != "order"},
            {**valid, "association": "fuzzy"},
            {**valid, "images": []},
            {**valid, "order": ["stop", "stop"]},
            {**valid, "images": [image(stamp="01")]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
