"""TC-P032-06 publication destination failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p032_tc06", Path(__file__).resolve().parents[1] / "gates" / "p032_tc06.py"
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
        "stage": "copy",
        "destinationFailure": "exhausted",
        "privateSource": "take-private.mp4",
        "stagingBytes": 4096,
        "publicationSucceeded": False,
        "deleteStagingBeforePublication": False,
        "successEntries": [],
    }
    base.update(overrides)
    return base


class TcP03206(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P032-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertNotIn("", result["preservedResults"])

    def test_copy_exhaustion_is_retryable_and_keeps_the_private_source(self):
        result = evaluate(payload(stage="copy", destinationFailure="exhausted"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retryable")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"][0], "take-private.mp4")
        self.assertIn("stage:copy", result["preservedResults"])
        self.assertIn("stagingBytes:4096", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], ["exhausted"])
        self.assertEqual(result["openQuestions"], ["retryable:copy"])
        self.assertTrue(any("no empty success entry" in item for item in result["reasons"]))

    def test_commit_grant_revocation_is_retryable(self):
        result = evaluate(payload(stage="commit", destinationFailure="grant_revoked"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retryable")
        self.assertIn("take-private.mp4", result["preservedResults"])
        self.assertIn("stage:commit", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], ["grant_revoked"])
        self.assertEqual(result["openQuestions"], ["retryable:commit"])

    def test_report_export_keeps_the_same_private_source(self):
        result = evaluate(payload(stage="report_export", destinationFailure="exhausted"))
        self.assertEqual(result["decision"], "retryable")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"][0], "take-private.mp4")
        self.assertIn("stage:report_export", result["preservedResults"])

    def test_negative_deleting_staging_before_publication_fails(self):
        result = evaluate(
            payload(deleteStagingBeforePublication=True, stage="redundant_staging_cleanup")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retryable"})
        self.assertIn("staging-deleted-before-publication", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], "take-private.mp4")
        self.assertIn("stagingBytes:4096", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_false_success_entries_are_rejected(self):
        result = evaluate(payload(successEntries=["published-id"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("false-success:published-id", result["rejectedClaims"])
        self.assertNotIn("published-id", result["preservedResults"])
        self.assertIn("take-private.mp4", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "stage": "upload"},
            {**valid, "stagingBytes": -1},
            {**valid, "privateSource": ""},
            {**valid, "successEntries": [""]},
            {**valid, "publicationSucceeded": "false"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
