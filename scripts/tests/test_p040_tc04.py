"""TC-P040-04 interrupted source tail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p040_tc04", Path(__file__).resolve().parents[1] / "gates" / "p040_tc04.py"
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
        "completeRecords": 3,
        "operation": "strict_development",
        "originalToken": "orig-raw",
        "prefixToken": "prefix-raw",
    }
    base.update(overrides)
    return base


class TcP04004(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P040-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("orig-raw", result["preservedResults"])

    def test_intervention_expected_and_negative_are_encoded(self):
        self.assertIn("Truncate a source", _MODULE.INTERVENTION)
        self.assertIn("complete-prefix recovery", _MODULE.EXPECTED)
        self.assertIn("Silently rewriting", _MODULE.NEGATIVE)

    def test_strict_development_rejects_a_payload_tail(self):
        result = evaluate(payload(boundary="payload"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "development_rejected")
        self.assertEqual(result["preservedResults"], ["orig-raw"])
        self.assertNotIn("prefix-raw", result["preservedResults"])
        self.assertIn("development rejected", result["openQuestions"])
        self.assertTrue(any("strict rejection is not prefix recovery" in item for item in result["reasons"]))
        self.assertIn("boundary:payload", result["reasons"])

    def test_strict_development_rejects_a_header_tail(self):
        result = evaluate(payload(boundary="header"))
        self.assertEqual(result["decision"], "development_rejected")
        self.assertEqual(result["preservedResults"], ["orig-raw"])
        self.assertIn("boundary:header", result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered"})

    def test_explicit_prefix_recovery_keeps_original_and_prefix(self):
        result = evaluate(payload(operation="explicit_prefix_recovery", boundary="checksum"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertEqual(result["preservedResults"], ["orig-raw", "prefix-raw"])
        self.assertIn("prefix recovery is explicit", result["openQuestions"])
        self.assertTrue(any("checksum" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_metadata_boundary_prefix_recovery_is_not_strict_acceptance(self):
        result = evaluate(
            payload(operation="explicit_prefix_recovery", boundary="metadata", completeRecords=2)
        )
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertIn("orig-raw", result["preservedResults"])
        self.assertIn("prefix-raw", result["preservedResults"])
        self.assertTrue(any("not strict acceptance" in item for item in result["reasons"]))

    def test_end_marker_without_records_is_withheld(self):
        result = evaluate(
            payload(boundary="end_marker", completeRecords=0, operation="explicit_prefix_recovery")
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], ["orig-raw"])
        self.assertIn("no complete prefix", result["openQuestions"])
        self.assertIn("boundary:end_marker", result["reasons"])

    def test_negative_silent_rewrite_fails(self):
        result = evaluate(payload(operation="silent_rewrite", boundary="payload"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "prefix_recovered"})
        self.assertEqual(result["rejectedClaims"], ["silent-rewrite"])
        self.assertEqual(result["preservedResults"], ["orig-raw"])
        self.assertNotIn("prefix-raw", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("shortened source was not substituted", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "boundary"},
            {**valid, "extra": True},
            {**valid, "boundary": "index"},
            {**valid, "completeRecords": -1},
            {**valid, "prefixToken": "orig-raw"},
            {**valid, "operation": "rewrite"},
            {**valid, "originalToken": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
