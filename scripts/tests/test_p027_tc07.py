"""TC-P027-07 deleting incomplete records on cold start is rejected."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc07", Path(__file__).resolve().parents[1] / "gates" / "p027_tc07.py"
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
        "transition": "before-first-sample",
        "deletedIncomplete": False,
        "knownRecords": ["clip-a"],
        "claimedVerified": False,
    }
    base.update(overrides)
    return base


class TcP02707(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("clean shutdown", _MODULE.INTERVENTION)
        self.assertIn("nonempty media", _MODULE.EXPECTED)
        self.assertIn("incomplete record", _MODULE.NEGATIVE)
        self.assertIn("before-first-sample", _MODULE.TRANSITIONS)
        self.assertIn("during-active-muxing", _MODULE.TRANSITIONS)
        self.assertIn("during-finalization", _MODULE.TRANSITIONS)
        self.assertIn("after-publication", _MODULE.TRANSITIONS)

    def test_before_first_sample_discovers_media_without_verification(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "discovered")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["clip-a", "before-first-sample"])

    def test_active_muxing_is_a_separate_repeat(self):
        result = evaluate(
            payload(transition="during-active-muxing", knownRecords=["clip-a", "clip-b"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "discovered")
        self.assertEqual(result["preservedResults"], ["clip-a", "clip-b", "during-active-muxing"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_deleting_incomplete_records_is_rejected_and_the_records_remain(self):
        result = evaluate(
            payload(transition="during-finalization", deletedIncomplete=True, knownRecords=["clip-a"])
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "discovered"})
        self.assertEqual(result["rejectedClaims"], ["incomplete-records-deleted"])
        self.assertIn("clip-a", result["preservedResults"])
        self.assertIn("during-finalization", result["preservedResults"])

    def test_claiming_verified_after_publication_is_still_rejected(self):
        result = evaluate(payload(transition="after-publication", claimedVerified=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "discovered"})
        self.assertIn("unfinished-claimed-verified", result["rejectedClaims"])
        self.assertIn("clip-a", result["preservedResults"])

    def test_empty_discovery_is_withheld(self):
        result = evaluate(payload(knownRecords=[]))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["before-first-sample"])
        self.assertTrue(any("no nonempty media" in item for item in result["openQuestions"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "transition": "startup"},
            {**valid, "knownRecords": ["clip-a", "clip-a"]},
            {**valid, "knownRecords": [1]},
            {**valid, "deletedIncomplete": "no"},
            {k: v for k, v in valid.items() if k != "claimedVerified"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
