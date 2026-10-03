"""TC-P038-04 strict rejection stays distinct from prefix recovery."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc04", Path(__file__).resolve().parents[1] / "gates" / "p038_tc04.py"
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
_TOKEN = "source-take-fw1"


def payload(**overrides):
    base = {
        "boundary": "payload",
        "completeRecords": 3,
        "truncatedInsideNext": True,
        "operation": "strict",
        "originalToken": _TOKEN,
    }
    base.update(overrides)
    return base


class TcP03804(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], _TOKEN)

    def test_strict_payload_rejection_keeps_the_original(self):
        result = evaluate(payload(boundary="payload"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["strict-development-rejected"])
        self.assertIn("completeRecords:3", result["preservedResults"])
        self.assertNotIn("recoveredRecords:3", result["preservedResults"])
        self.assertTrue(any("strict development rejected" in item for item in result["reasons"]))

    def test_explicit_prefix_recovery_is_a_different_decision(self):
        result = evaluate(payload(boundary="checksum", operation="recover-prefix"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertNotEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"][0], _TOKEN)
        self.assertIn("recoveredRecords:3", result["preservedResults"])
        self.assertTrue(any("distinct" in item for item in result["reasons"]))

    def test_header_and_end_marker_boundaries(self):
        header = evaluate(payload(boundary="header", completeRecords=0, operation="recover-prefix"))
        self.assertEqual(header["decision"], "withheld")
        self.assertEqual(header["preservedResults"][0], _TOKEN)
        self.assertFalse(any(item.startswith("recoveredRecords:") for item in header["preservedResults"]))
        end = evaluate(payload(boundary="end-marker", operation="strict"))
        self.assertEqual(end["decision"], "rejected")
        self.assertIn("boundary:end-marker", end["preservedResults"])
        self.assertIn(_TOKEN, end["preservedResults"])

    def test_metadata_boundary_strict_versus_recovery(self):
        strict = evaluate(payload(boundary="metadata", operation="strict"))
        recovered = evaluate(payload(boundary="metadata", operation="recover-prefix"))
        self.assertEqual(strict["decision"], "rejected")
        self.assertEqual(recovered["decision"], "prefix_recovered")
        self.assertNotEqual(strict["decision"], recovered["decision"])
        self.assertEqual(strict["preservedResults"][0], recovered["preservedResults"][0])

    def test_silent_rewrite_fails_and_does_not_replace_the_original(self):
        result = evaluate(payload(operation="silent-rewrite", boundary="payload"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-rewrite"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][0], _TOKEN)
        self.assertNotIn("shortened", " ".join(result["preservedResults"]))
        self.assertFalse(any(item.startswith("recoveredRecords:") for item in result["preservedResults"]))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(boundary="footer"))
        with self.assertRaises(ValueError):
            evaluate(payload(operation="rewrite"))


if __name__ == "__main__":
    unittest.main()
