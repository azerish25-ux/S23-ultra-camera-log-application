"""TC-P027-06 staging deleted before publication is rejected."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc06", Path(__file__).resolve().parents[1] / "gates" / "p027_tc06.py"
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
        "stagingDeleted": False,
        "privateSource": "private-source-p027",
        "privateSourceRetained": True,
        "retryable": True,
        "emptySuccessEntry": False,
        "publicationSucceeded": False,
    }
    base.update(overrides)
    return base


class TcP02706(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("publication grant", _MODULE.INTERVENTION)
        self.assertIn("retryable recovery", _MODULE.EXPECTED)
        self.assertIn("Deleting staging", _MODULE.NEGATIVE)
        self.assertIn("copy", _MODULE.STAGES)
        self.assertIn("commit", _MODULE.STAGES)
        self.assertIn("report-export", _MODULE.STAGES)
        self.assertIn("redundant-staging-cleanup", _MODULE.STAGES)

    def test_copy_failure_keeps_a_retryable_private_source(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retryable")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["private-source-p027", "copy"])

    def test_commit_is_a_separate_repeat(self):
        result = evaluate(payload(stage="commit"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retryable")
        self.assertEqual(result["preservedResults"], ["private-source-p027", "commit"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_deleting_staging_before_publication_is_rejected(self):
        result = evaluate(payload(stage="report-export", stagingDeleted=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retryable"})
        self.assertIn("staging-deleted-before-publication", result["rejectedClaims"])
        self.assertIn("private-source-p027", result["preservedResults"])
        self.assertIn("report-export", result["preservedResults"])

    def test_empty_success_and_lost_source_stay_in_the_inventory(self):
        result = evaluate(
            payload(
                stage="redundant-staging-cleanup",
                privateSourceRetained=False,
                retryable=False,
                emptySuccessEntry=True,
                publicationSucceeded=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("private-source-lost", result["rejectedClaims"])
        self.assertIn("not-retryable", result["rejectedClaims"])
        self.assertIn("empty-success-entry", result["rejectedClaims"])
        self.assertIn("false-publication-success", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], "private-source-p027")

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "stage": "publish"},
            {**valid, "privateSource": ""},
            {**valid, "stagingDeleted": "false"},
            {**valid, "emptySuccessEntry": 0},
            {k: v for k, v in valid.items() if k != "retryable"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
