"""TC-P028-07 cold start keeps incomplete media unverified."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc07", Path(__file__).resolve().parents[1] / "gates" / "p028_tc07.py"
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
_MEDIA = "private-stage/take-p028.mp4"


def payload(**overrides):
    base = {
        "transition": "during_active_muxing",
        "cleanShutdown": False,
        "retainedMedia": [_MEDIA],
        "mediaNonempty": True,
        "deleteIncompleteOnStartup": False,
        "claimVerified": False,
    }
    base.update(overrides)
    return base


class TcP02807(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("clean shutdown", _MODULE.INTERVENTION)
        self.assertIn("unfinished output", _MODULE.EXPECTED)
        self.assertIn("incomplete record", _MODULE.NEGATIVE)
        self.assertIn("before_first_sample", _MODULE._TRANSITIONS)
        self.assertIn("during_active_muxing", _MODULE._TRANSITIONS)
        self.assertIn("during_finalization", _MODULE._TRANSITIONS)
        self.assertIn("after_publication", _MODULE._TRANSITIONS)

    def test_before_first_sample_with_no_media_is_withheld(self):
        result = evaluate(
            payload(
                transition="before_first_sample",
                retainedMedia=[],
                mediaNonempty=False,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "recovered_unverified"})
        self.assertIn("transition:before_first_sample", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_during_active_muxing_recovers_unverified_media(self):
        result = evaluate(payload(transition="during_active_muxing"))
        self.assertEqual(result["decision"], "recovered_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MEDIA, result["preservedResults"])
        self.assertIn("transition:during_active_muxing", result["preservedResults"])
        self.assertTrue(any("no clean shutdown" in item for item in result["reasons"]))

    def test_during_finalization_does_not_claim_verified(self):
        result = evaluate(payload(transition="during_finalization"))
        self.assertEqual(result["decision"], "recovered_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MEDIA, result["preservedResults"])
        self.assertIn("transition:during_finalization", result["preservedResults"])

    def test_after_publication_stays_unverified(self):
        result = evaluate(payload(transition="after_publication", cleanShutdown=True))
        self.assertEqual(result["decision"], "recovered_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MEDIA, result["preservedResults"])
        self.assertIn("transition:after_publication", result["preservedResults"])

    def test_deleting_incomplete_records_is_rejected(self):
        result = evaluate(
            payload(transition="during_active_muxing", deleteIncompleteOnStartup=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "recovered_unverified"})
        self.assertIn("incomplete-records-deleted", result["rejectedClaims"])
        self.assertIn(_MEDIA, result["preservedResults"])

    def test_claiming_unfinished_output_verified_is_rejected(self):
        result = evaluate(payload(transition="during_finalization", claimVerified=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("unfinished-output-claimed-verified", result["rejectedClaims"])
        self.assertIn(_MEDIA, result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "transition": "later"},
            {**valid, "mediaNonempty": False},
            {**valid, "retainedMedia": ["", _MEDIA]},
            {**valid, "claimVerified": "yes"},
            {k: v for k, v in valid.items() if k != "transition"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
