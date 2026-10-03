"""TC-P034-04 interrupted source tail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc04", Path(__file__).resolve().parents[1] / "gates" / "p034_tc04.py"
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
        "operation": "strict_reject",
        "originalId": "src-1",
    }
    base.update(overrides)
    return base


class TcP03404(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("Truncate a source", _MODULE.INTERVENTION)
        self.assertIn("complete-prefix recovery", _MODULE.EXPECTED)
        self.assertIn("Silently rewriting", _MODULE.NEGATIVE)
        self.assertEqual(
            _MODULE.BOUNDARIES,
            ("header", "metadata", "payload", "checksum", "end_marker"),
        )

    def test_header_boundary_strict_rejection_keeps_original(self):
        result = evaluate(payload(boundary="header", completeRecords=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "development_rejected")
        self.assertIn("boundary:header", result["preservedResults"])
        self.assertIn("complete:0", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["rejected-at:header"])

    def test_payload_boundary_strict_rejection_is_distinct(self):
        result = evaluate(payload(boundary="payload"))
        self.assertEqual(result["decision"], "development_rejected")
        self.assertIn("boundary:payload", result["preservedResults"])
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertNotEqual(result["decision"], "prefix_recovered")

    def test_checksum_prefix_recovery_keeps_original_and_prefix(self):
        result = evaluate(payload(boundary="checksum", operation="prefix_recovery", completeRecords=3))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertIn("recovered-prefix:3", result["preservedResults"])
        self.assertIn("boundary:checksum", result["preservedResults"])
        self.assertNotEqual(result["decision"], "development_rejected")

    def test_end_marker_prefix_recovery_is_not_acceptance(self):
        strict = evaluate(payload(boundary="end_marker", operation="strict_reject"))
        recovered = evaluate(payload(boundary="end_marker", operation="prefix_recovery"))
        self.assertEqual(strict["decision"], "development_rejected")
        self.assertEqual(recovered["decision"], "prefix_recovered")
        self.assertNotEqual(strict["decision"], recovered["decision"])
        self.assertIn("original:src-1", strict["preservedResults"])
        self.assertIn("original:src-1", recovered["preservedResults"])
        self.assertIn("boundary:end_marker", recovered["preservedResults"])

    def test_metadata_boundary_is_recorded(self):
        result = evaluate(payload(boundary="metadata", completeRecords=1))
        self.assertEqual(result["decision"], "development_rejected")
        self.assertIn("boundary:metadata", result["preservedResults"])
        self.assertIn("complete:1", result["preservedResults"])

    def test_negative_silent_rewrite_fails_and_keeps_original(self):
        result = evaluate(payload(operation="silent_rewrite"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered", "development_rejected"})
        self.assertEqual(result["rejectedClaims"], ["silent-rewrite"])
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertIn("complete:2", result["preservedResults"])
        self.assertNotIn("recovered-prefix:2", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(boundary="footer"))
        with self.assertRaises(ValueError):
            evaluate(payload(completeRecords=-1))


if __name__ == "__main__":
    unittest.main()
