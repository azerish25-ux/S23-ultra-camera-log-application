"""TC-P026-07 cold start keeps incomplete media unverified."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc07", Path(__file__).resolve().parents[1] / "gates" / "p026_tc07.py"
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
        "transition": "before_first_sample",
        "cleanShutdown": False,
        "mediaId": "journal-header",
        "mediaNonempty": True,
        "deletesIncomplete": False,
        "claimsVerified": False,
    }
    base.update(overrides)
    return base


class TcP02607(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "verified"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("journal transition", _MODULE.INTERVENTION)
        self.assertIn("nonempty media", _MODULE.EXPECTED)
        self.assertIn("incomplete record", _MODULE.NEGATIVE)
        self.assertIn("before_first_sample", _MODULE.TRANSITIONS)
        self.assertIn("during_active_muxing", _MODULE.TRANSITIONS)

    def test_before_first_sample_retains_media_without_verifying_it(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_unverified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["journal-header", "transition:before_first_sample"],
        )
        self.assertTrue(any("not verified" in item for item in result["reasons"]))

    def test_active_muxing_is_retained_not_verified(self):
        result = evaluate(
            payload(transition="during_active_muxing", mediaId="mux-fragment")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "verified"})
        self.assertIn("mux-fragment", result["preservedResults"])
        self.assertIn("transition:during_active_muxing", result["preservedResults"])

    def test_deleting_incomplete_records_fails_and_keeps_the_media_id(self):
        result = evaluate(
            payload(
                transition="during_finalization",
                mediaId="final-fragment",
                deletesIncomplete=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("incomplete-records-deleted", result["rejectedClaims"])
        self.assertIn("final-fragment", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "verified"})

    def test_claiming_finalization_verified_fails(self):
        result = evaluate(payload(transition="during_finalization", claimsVerified=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unfinished-claimed-verified", result["rejectedClaims"])
        self.assertIn("journal-header", result["preservedResults"])

    def test_publication_is_still_not_a_verified_claim(self):
        result = evaluate(
            payload(transition="after_publication", mediaId="published-copy", claimsVerified=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unfinished-claimed-verified", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "verified"})
        self.assertIn("published-copy", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "transition": "later"},
            {**valid, "mediaId": ""},
            {**valid, "mediaNonempty": "yes"},
            {k: v for k, v in valid.items() if k != "mediaId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
