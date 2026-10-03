"""TC-P028-06 publication failure keeps the private source."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc06", Path(__file__).resolve().parents[1] / "gates" / "p028_tc06.py"
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
_SOURCE = "private-stage/take-p028.mp4"


def payload(**overrides):
    base = {
        "stage": "copy",
        "destinationFailure": "exhausted",
        "privateSource": _SOURCE,
        "stagingBytes": 4096,
        "publicationSucceeded": False,
        "deleteStagingBeforePublication": False,
        "successEntries": [],
    }
    base.update(overrides)
    return base


class TcP02806(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("publication grant", _MODULE.INTERVENTION)
        self.assertIn("retryable", _MODULE.EXPECTED)
        self.assertIn("Deleting staging", _MODULE.NEGATIVE)

    def test_copy_with_exhausted_space_is_retryable(self):
        result = evaluate(payload(stage="copy", destinationFailure="exhausted"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retryable")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("exhausted", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _SOURCE)
        self.assertIn("stage:copy", result["preservedResults"])
        self.assertTrue(any("no empty success entry" in item for item in result["reasons"]))

    def test_commit_with_grant_revoked_is_retryable(self):
        result = evaluate(payload(stage="commit", destinationFailure="grant_revoked"))
        self.assertEqual(result["decision"], "retryable")
        self.assertIn("grant_revoked", result["rejectedClaims"])
        self.assertIn(_SOURCE, result["preservedResults"])
        self.assertIn("stage:commit", result["preservedResults"])

    def test_report_export_deleting_staging_is_rejected(self):
        result = evaluate(
            payload(
                stage="report_export",
                destinationFailure="none",
                deleteStagingBeforePublication=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retryable"})
        self.assertIn("staging-deleted-before-publication", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _SOURCE)

    def test_redundant_staging_cleanup_deleting_early_is_rejected(self):
        result = evaluate(
            payload(
                stage="redundant_staging_cleanup",
                destinationFailure="exhausted",
                deleteStagingBeforePublication=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("staging-deleted-before-publication", result["rejectedClaims"])
        self.assertIn("exhausted", result["rejectedClaims"])
        self.assertIn(_SOURCE, result["preservedResults"])

    def test_false_success_entries_are_rejected(self):
        result = evaluate(payload(successEntries=["published-take"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("false-success:published-take", result["rejectedClaims"])
        self.assertIn(_SOURCE, result["preservedResults"])

    def test_recorded_publication_is_not_physical_qualification(self):
        result = evaluate(
            payload(
                stage="commit",
                destinationFailure="none",
                publicationSucceeded=True,
                successEntries=["published-take"],
            )
        )
        self.assertEqual(result["decision"], "publication_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_SOURCE, result["preservedResults"])
        self.assertTrue(any("not a physical S23" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "stage": "upload"},
            {**valid, "successEntries": [""]},
            {**valid, "stagingBytes": -1},
            {**valid, "privateSource": "  "},
            {k: v for k, v in valid.items() if k != "privateSource"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
