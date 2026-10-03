"""TC-P026-06 publication failure keeps the private source retryable."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc06", Path(__file__).resolve().parents[1] / "gates" / "p026_tc06.py"
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
_SOURCE = "private-take-p026"


def payload(**overrides):
    base = {
        "stage": "copy",
        "destinationExhausted": True,
        "grantRevoked": False,
        "stagingPresent": True,
        "deletedBeforePublication": False,
        "privateSourceId": _SOURCE,
        "emptySuccess": False,
    }
    base.update(overrides)
    return base


class TcP02606(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("publication grant", _MODULE.INTERVENTION)
        self.assertIn("retryable", _MODULE.EXPECTED)
        self.assertIn("Deleting staging", _MODULE.NEGATIVE)
        self.assertIn("copy", _MODULE.STAGES)
        self.assertIn("report_export", _MODULE.STAGES)

    def test_copy_exhaustion_is_retryable_and_keeps_the_private_source(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retryable")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [_SOURCE, "stage:copy"])

    def test_report_export_grant_revocation_is_also_retryable(self):
        result = evaluate(
            payload(stage="report_export", destinationExhausted=False, grantRevoked=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "retryable")
        self.assertIn(_SOURCE, result["preservedResults"])
        self.assertIn("stage:report_export", result["preservedResults"])

    def test_deleting_staging_before_publication_fails(self):
        result = evaluate(payload(stage="commit", deletedBeforePublication=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("staging-deleted-before-publication", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retryable"})
        self.assertEqual(result["preservedResults"][0], _SOURCE)

    def test_empty_success_is_rejected_during_cleanup(self):
        result = evaluate(payload(stage="redundant_staging_cleanup", emptySuccess=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("empty-success-entry", result["rejectedClaims"])
        self.assertIn(_SOURCE, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "stage": "publish"},
            {**valid, "privateSourceId": ""},
            {**valid, "emptySuccess": "yes"},
            {k: v for k, v in valid.items() if k != "privateSourceId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
