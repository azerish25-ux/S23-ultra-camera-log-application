"""TC-P033-04 interrupted source tail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc04", Path(__file__).resolve().parents[1] / "gates" / "p033_tc04.py"
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
_RECORDS = ["f0", "f1", "f2"]


def payload(**overrides):
    base = {
        "completeRecords": 3,
        "recordIds": list(_RECORDS),
        "boundary": "payload",
        "mode": "strict",
        "rewriteOriginal": False,
    }
    base.update(overrides)
    return base


class TcP03304(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-04")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])
        for record in _RECORDS:
            self.assertIn("record:" + record, result["preservedResults"])
        self.assertIn("original:unmodified", result["preservedResults"])

    def test_strict_and_recovery_are_distinct(self):
        strict = evaluate(payload(mode="strict", boundary="payload"))
        recovered = evaluate(payload(mode="recovery", boundary="payload"))
        self.assertContract(strict)
        self.assertContract(recovered)
        self.assertEqual(strict["decision"], "development_rejected")
        self.assertEqual(recovered["decision"], "prefix_recovered")
        self.assertNotEqual(strict["decision"], recovered["decision"])
        self.assertNotIn(strict["decision"], _FORBIDDEN)
        self.assertNotIn(recovered["decision"], _FORBIDDEN)
        self.assertIn(_MODULE.EXPECTED, strict["reasons"])
        self.assertIn(_MODULE.EXPECTED, recovered["reasons"])
        self.assertEqual(strict["rejectedClaims"], ["truncated-payload"])
        self.assertEqual(recovered["rejectedClaims"], ["truncated-payload"])

    def test_repeat_header_and_metadata_boundaries(self):
        for boundary in ("header", "metadata"):
            result = evaluate(payload(boundary=boundary, mode="recovery", completeRecords=0, recordIds=[]))
            self.assertEqual(result["caseId"], "TC-P033-04")
            self.assertEqual(result["decision"], "prefix_recovered")
            self.assertNotIn(result["decision"], _FORBIDDEN)
            self.assertIn("truncated-" + boundary, result["rejectedClaims"])
            self.assertIn("boundary:" + boundary, result["preservedResults"])
            self.assertIn("complete:0", result["preservedResults"])
            self.assertIn("original:unmodified", result["preservedResults"])

    def test_repeat_payload_checksum_and_end_marker(self):
        for boundary in ("payload", "checksum", "end-marker"):
            result = evaluate(payload(boundary=boundary, mode="strict"))
            self.assertContract(result)
            self.assertEqual(result["decision"], "development_rejected")
            self.assertIn("truncated-" + boundary, result["rejectedClaims"])
            self.assertIn("boundary:" + boundary, result["preservedResults"])
            self.assertIn("record:f0", result["preservedResults"])

    def test_negative_silent_rewrite_fails(self):
        result = evaluate(payload(mode="recovery", rewriteOriginal=True, boundary="checksum"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"prefix_recovered", "development_rejected"})
        self.assertEqual(result["rejectedClaims"], ["silent-rewrite", "truncated-checksum"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("record:f2", result["preservedResults"])
        self.assertIn("original:unmodified", result["preservedResults"])
        self.assertIn("boundary:checksum", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "boundary": "footer"},
            {**valid, "mode": "rewrite"},
            {**valid, "completeRecords": -1},
            {**valid, "recordIds": ["f0"]},
            {**valid, "recordIds": ["f0", "f0", "f1"]},
            {**valid, "rewriteOriginal": 1},
            {**valid, "completeRecords": 0, "recordIds": ["f0"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
