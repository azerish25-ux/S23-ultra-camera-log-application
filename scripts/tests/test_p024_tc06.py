"""TC-P024-06 recreation keeps committed control separate from a draft."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p024_tc06", Path(__file__).resolve().parents[1] / "gates" / "p024_tc06.py"
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
        "recreation": "rotation",
        "committed": "iso=400",
        "draft": "iso=800",
        "draftAppliedToCamera": False,
        "draftSeparated": True,
        "invalidPartial": False,
    }
    base.update(overrides)
    return base


class TcP02406(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P024-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("unapplied or invalid control draft", _MODULE.INTERVENTION)
        self.assertIn("committed effective state", _MODULE.EXPECTED)
        self.assertIn("invalid partial numeric entry", _MODULE.NEGATIVE)
        self.assertIn("rotation", _MODULE.RECREATIONS)
        self.assertIn("cancelled_edits", _MODULE.RECREATIONS)

    def test_rotation_keeps_committed_state_and_the_draft(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "committed_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["committed:iso=400", "draft:iso=800"])
        self.assertIn("restored draft is not applied sensor control", result["openQuestions"])
        self.assertTrue(any("rotation" in item for item in result["reasons"]))
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_process_recreation_without_a_draft_keeps_committed_state(self):
        result = evaluate(
            payload(
                recreation="process_recreation",
                committed="shutter=1/48",
                draft=None,
                draftSeparated=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "committed_preserved")
        self.assertEqual(result["preservedResults"], ["committed:shutter=1/48"])
        self.assertEqual(result["openQuestions"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_partial_on_manual_transition_is_rejected(self):
        result = evaluate(
            payload(
                recreation="manual_mode_transition",
                committed="iso=200",
                draft="12.",
                draftAppliedToCamera=True,
                draftSeparated=False,
                invalidPartial=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "committed_preserved"})
        self.assertIn("invalid-partial-applied", result["rejectedClaims"])
        self.assertIn("draft-applied-to-camera", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["committed:iso=200", "draft:12."])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_cancelled_edit_that_is_not_separated_is_rejected(self):
        result = evaluate(
            payload(
                recreation="cancelled_edits",
                committed="wb=5600K",
                draft="wb=3200K",
                draftSeparated=False,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("draft-not-separated", result["rejectedClaims"])
        self.assertIn("committed:wb=5600K", result["preservedResults"])
        self.assertIn("draft:wb=3200K", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "recreation": "theme_change"},
            {**valid, "draft": None, "draftAppliedToCamera": True},
            {**valid, "invalidPartial": "yes"},
            {**valid, "committed": ""},
            {key: value for key, value in valid.items() if key != "recreation"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
