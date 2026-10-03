"""TC-P025-07 cold-start recovery."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p025_tc07", Path(__file__).resolve().parents[1] / "gates" / "p025_tc07.py"
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
        "retainedMedia": [],
        "mediaNonempty": False,
        "deleteIncompleteOnStartup": False,
        "claimVerified": False,
    }
    base.update(overrides)
    return base


class TcP02507(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P025-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_before_first_sample_does_not_invent_media(self):
        result = evaluate(payload(transition="before_first_sample"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("transition:before_first_sample", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["no nonempty media discovered"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_active_muxing_recovers_media_without_verification(self):
        result = evaluate(
            payload(
                transition="active_muxing",
                retainedMedia=["mux-partial.mp4"],
                mediaNonempty=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "recovered_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("mux-partial.mp4", result["preservedResults"])
        self.assertIn("transition:active_muxing", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["retained media is not a verified output"])

    def test_finalization_keeps_the_partial_name(self):
        result = evaluate(
            payload(
                transition="finalization",
                retainedMedia=["final-partial.mp4"],
                mediaNonempty=True,
            )
        )
        self.assertEqual(result["decision"], "recovered_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("final-partial.mp4", result["preservedResults"])
        self.assertIn("transition:finalization", result["preservedResults"])

    def test_after_publication_is_still_not_a_verified_claim(self):
        result = evaluate(
            payload(
                transition="after_publication",
                retainedMedia=["published.mp4"],
                mediaNonempty=True,
                cleanShutdown=True,
            )
        )
        self.assertEqual(result["decision"], "recovered_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("published.mp4", result["preservedResults"])

    def test_negative_deleting_incomplete_records_fails(self):
        result = evaluate(
            payload(
                transition="active_muxing",
                retainedMedia=["mux-partial.mp4"],
                mediaNonempty=True,
                deleteIncompleteOnStartup=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("incomplete-records-deleted", result["rejectedClaims"])
        self.assertIn("mux-partial.mp4", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_claiming_unfinished_output_verified_fails(self):
        result = evaluate(
            payload(
                transition="finalization",
                retainedMedia=["final-partial.mp4"],
                mediaNonempty=True,
                claimVerified=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unfinished-output-claimed-verified", result["rejectedClaims"])
        self.assertIn("final-partial.mp4", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "transition": "booting"},
            {**valid, "mediaNonempty": True},
            {**valid, "retainedMedia": [""], "mediaNonempty": True},
            {**valid, "cleanShutdown": "no"},
            {**valid, "claimVerified": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
