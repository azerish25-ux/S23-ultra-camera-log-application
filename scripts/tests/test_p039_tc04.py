"""TC-P039-04 interrupted source tail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc04", Path(__file__).resolve().parents[1] / "gates" / "p039_tc04.py"
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
        "completeRecords": ["rec-0", "rec-1"],
        "cutAt": "payload",
        "operation": "strict",
        "originalSource": "take.rawseq",
    }
    base.update(overrides)
    return base


class TcP03904(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_strict_payload_cut_is_not_recovery(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "development_rejected")
        self.assertIn("incomplete-tail", result["rejectedClaims"])
        self.assertIn("original:take.rawseq", result["preservedResults"])
        self.assertIn("complete:rec-0", result["preservedResults"])
        self.assertNotIn("recovered:rec-0", result["preservedResults"])

    def test_strict_checksum_cut_stays_distinct(self):
        result = evaluate(payload(cutAt="checksum"))
        self.assertEqual(result["decision"], "development_rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered"})
        self.assertIn("original:take.rawseq", result["preservedResults"])
        self.assertIn("complete:rec-1", result["preservedResults"])

    def test_explicit_prefix_recovery_at_end_marker(self):
        result = evaluate(payload(cutAt="end_marker", operation="recover_prefix"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("original:take.rawseq", result["preservedResults"])
        self.assertIn("recovered:rec-0", result["preservedResults"])
        self.assertIn("recovered:rec-1", result["preservedResults"])

    def test_metadata_boundary_recovery_keeps_the_original(self):
        result = evaluate(payload(cutAt="metadata", operation="recover_prefix"))
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertIn("original:take.rawseq", result["preservedResults"])
        self.assertIn("complete:rec-1", result["preservedResults"])

    def test_silent_rewrite_negative_is_rejected(self):
        result = evaluate(payload(operation="silent_rewrite"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-rewrite", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("original:take.rawseq", result["preservedResults"])
        self.assertIn("complete:rec-0", result["preservedResults"])
        self.assertNotIn("recovered:rec-0", result["preservedResults"])


if __name__ == "__main__":
    unittest.main()
