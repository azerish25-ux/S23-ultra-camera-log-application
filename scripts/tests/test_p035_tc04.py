"""TC-P035-04 interrupted source tail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc04", Path(__file__).resolve().parents[1] / "gates" / "p035_tc04.py"
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
        "boundary": "payload",
        "completeRecords": 2,
        "operation": "strict",
        "originalToken": "file:s23raw:abc",
    }
    base.update(overrides)
    return base


class TcP03504(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_repeat_header_strict_is_not_recovery(self):
        result = evaluate(payload(boundary="header", completeRecords=0, operation="strict"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "strict_rejected")
        self.assertIn("original:file:s23raw:abc", result["preservedResults"])
        self.assertIn("boundary:header", result["preservedResults"])
        self.assertIn("complete-records:0", result["preservedResults"])
        self.assertNotIn("prefix-records:0", result["preservedResults"])

    def test_repeat_checksum_prefix_recovery_keeps_original(self):
        result = evaluate(payload(boundary="checksum", operation="recover_prefix", completeRecords=3))
        self.assertContract(result)
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertIn("original:file:s23raw:abc", result["preservedResults"])
        self.assertIn("prefix-records:3", result["preservedResults"])
        self.assertIn("boundary:checksum", result["preservedResults"])
        self.assertNotEqual(result["decision"], "strict_rejected")
        self.assertIn("not a completed source", result["openQuestions"][0])

    def test_payload_strict_and_recovery_stay_distinct(self):
        strict = evaluate(payload(boundary="payload", operation="strict"))
        recovered = evaluate(payload(boundary="payload", operation="recover_prefix"))
        self.assertEqual(strict["decision"], "strict_rejected")
        self.assertEqual(recovered["decision"], "prefix_recovered")
        self.assertEqual(strict["preservedResults"][0], recovered["preservedResults"][0])
        self.assertIn(_MODULE.EXPECTED, strict["reasons"])

    def test_repeat_end_marker_does_not_rewrite(self):
        result = evaluate(payload(boundary="end_marker", operation="strict", completeRecords=1))
        self.assertEqual(result["decision"], "strict_rejected")
        self.assertIn("boundary:end_marker", result["preservedResults"])
        self.assertIn("original:file:s23raw:abc", result["preservedResults"])

    def test_negative_silent_rewrite_fails(self):
        result = evaluate(payload(operation="rewrite_short", boundary="metadata"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-rewrite"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("original:file:s23raw:abc", result["preservedResults"])
        self.assertIn("complete-records:2", result["preservedResults"])
        self.assertFalse(any(item.startswith("rewritten:") for item in result["preservedResults"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "boundary": "footer"},
            {**valid, "boundary": "header", "completeRecords": 1},
            {**valid, "completeRecords": 0},
            {**valid, "originalToken": ""},
            {key: value for key, value in valid.items() if key != "operation"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
