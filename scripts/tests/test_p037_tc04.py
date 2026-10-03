"""TC-P037-04 interrupted source tail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc04", Path(__file__).resolve().parents[1] / "gates" / "p037_tc04.py"
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
        "completeRecords": ["f0", "f1"],
        "cutAt": "payload",
        "operation": "strict",
        "originalSource": "source.raw",
    }
    base.update(overrides)
    return base


class TcP03704(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_strict_payload_cut_is_development_rejected(self):
        result = evaluate(payload(cutAt="payload"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "development_rejected")
        self.assertIn("incomplete-tail", result["rejectedClaims"])
        self.assertIn("original:source.raw", result["preservedResults"])
        self.assertIn("complete:f0", result["preservedResults"])
        self.assertNotIn("recovered:f0", result["preservedResults"])

    def test_strict_checksum_cut_stays_distinct_from_recovery(self):
        strict = evaluate(payload(cutAt="checksum"))
        recovered = evaluate(payload(cutAt="checksum", operation="recover_prefix"))
        self.assertEqual(strict["decision"], "development_rejected")
        self.assertEqual(recovered["decision"], "prefix_recovered")
        self.assertNotEqual(strict["decision"], recovered["decision"])
        self.assertIn("original:source.raw", recovered["preservedResults"])
        self.assertIn("recovered:f1", recovered["preservedResults"])
        self.assertNotIn(recovered["decision"], {"qualified", "allowed"})

    def test_end_marker_recovery_keeps_the_original(self):
        result = evaluate(payload(cutAt="end_marker", operation="recover_prefix"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertIn("original:source.raw", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["recovered 2 complete records"])

    def test_silent_rewrite_fails(self):
        result = evaluate(payload(operation="silent_rewrite", cutAt="metadata"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered"})
        self.assertIn("silent-rewrite", result["rejectedClaims"])
        self.assertIn("original:source.raw", result["preservedResults"])
        self.assertIn("complete:f0", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_header_cut_has_no_prefix_to_recover(self):
        result = evaluate(payload(completeRecords=[], cutAt="header", operation="recover_prefix"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("no-complete-prefix", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["original:source.raw"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "cutAt": "footer"},
            {**valid, "completeRecords": ["f0"], "cutAt": "header"},
            {**valid, "operation": "rewrite"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
