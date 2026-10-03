"""TC-P036-04 interrupted source tail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc04", Path(__file__).resolve().parents[1] / "gates" / "p036_tc04.py"
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
_ORIGINAL = "source-tail-original"
_PREFIX = "source-tail-prefix"


def payload(**overrides):
    base = {
        "boundary": "payload",
        "completeRecords": 2,
        "operation": "strict_development",
        "originalToken": _ORIGINAL,
        "prefixToken": _PREFIX,
    }
    base.update(overrides)
    return base


class TcP03604(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], _ORIGINAL)

    def test_header_boundary_strict_rejection_keeps_original(self):
        result = evaluate(payload(boundary="header", completeRecords=0))
        self.assertContract(result)
        self.assertEqual(result["decision"], "development_rejected")
        self.assertEqual(result["preservedResults"], [_ORIGINAL])
        self.assertNotIn(_PREFIX, result["preservedResults"])
        self.assertTrue(any("boundary:header" in item for item in result["reasons"]))

    def test_checksum_boundary_strict_rejection_is_not_recovery(self):
        result = evaluate(payload(boundary="checksum", completeRecords=3))
        self.assertEqual(result["decision"], "development_rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered"})
        self.assertEqual(result["preservedResults"], [_ORIGINAL])
        self.assertTrue(any("not prefix recovery" in item for item in result["reasons"]))

    def test_explicit_prefix_recovery_keeps_original_and_prefix(self):
        strict = evaluate(payload(boundary="payload"))
        recovered = evaluate(payload(boundary="payload", operation="explicit_prefix_recovery"))
        self.assertEqual(strict["decision"], "development_rejected")
        self.assertEqual(recovered["decision"], "prefix_recovered")
        self.assertNotEqual(strict["decision"], recovered["decision"])
        self.assertEqual(recovered["preservedResults"], [_ORIGINAL, _PREFIX])
        self.assertNotIn(recovered["decision"], {"qualified", "allowed"})
        self.assertTrue(any("not strict acceptance" in item for item in recovered["reasons"]))

    def test_end_marker_without_complete_records_is_withheld(self):
        result = evaluate(
            payload(boundary="end_marker", completeRecords=0, operation="explicit_prefix_recovery")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], [_ORIGINAL])
        self.assertIn("no complete prefix", result["openQuestions"])

    def test_metadata_boundary_recovery_when_records_exist(self):
        result = evaluate(
            payload(boundary="metadata", completeRecords=1, operation="explicit_prefix_recovery")
        )
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertEqual(result["preservedResults"][0], _ORIGINAL)
        self.assertIn(_PREFIX, result["preservedResults"])

    def test_negative_silent_rewrite_fails_and_keeps_original(self):
        result = evaluate(payload(operation="silent_rewrite", boundary="payload"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered"})
        self.assertEqual(result["rejectedClaims"], ["silent-rewrite"])
        self.assertEqual(result["preservedResults"], [_ORIGINAL])
        self.assertNotIn(_PREFIX, result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "boundary": "tail"},
            {**valid, "completeRecords": -1},
            {**valid, "originalToken": _PREFIX, "prefixToken": _PREFIX},
            {**valid, "operation": "rewrite"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
