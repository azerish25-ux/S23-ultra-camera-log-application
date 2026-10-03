"""TC-P023-06 recreation must not apply an invalid control draft."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p023_tc06", Path(__file__).resolve().parents[1] / "gates" / "p023_tc06.py"
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
        "committed": "iso:400",
        "draft": "iso:4",
        "draftAppliedToCamera": False,
        "draftSeparated": True,
        "invalidPartial": True,
    }
    base.update(overrides)
    return base


class TcP02306(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P023-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("unapplied or invalid control draft", _MODULE.INTERVENTION)
        self.assertIn("committed effective state", _MODULE.EXPECTED)
        self.assertIn("invalid partial numeric entry", _MODULE.NEGATIVE)
        self.assertIn("rotation", _MODULE.RECREATIONS)
        self.assertIn("cancelled_edits", _MODULE.RECREATIONS)

    def test_rotation_keeps_committed_state_and_separate_draft(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "committed_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["committed:iso:400", "draft:iso:4"])
        self.assertIn("restored draft is not applied sensor control", result["openQuestions"])
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_process_recreation_preserves_committed_manual_value(self):
        result = evaluate(
            payload(
                recreation="process_recreation",
                committed="shutter:1/48",
                draft="shutter:1/",
                invalidPartial=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "committed_preserved")
        self.assertEqual(result["preservedResults"][0], "committed:shutter:1/48")
        self.assertIn("draft:shutter:1/", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_partial_reaching_camera_is_rejected(self):
        result = evaluate(payload(recreation="manual_mode_transition", draftAppliedToCamera=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "committed_preserved"})
        self.assertIn("invalid-partial-applied", result["rejectedClaims"])
        self.assertIn("draft-applied-to-camera", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["committed:iso:400", "draft:iso:4"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_cancelled_edits_drop_the_draft_and_keep_committed(self):
        result = evaluate(
            payload(
                recreation="cancelled_edits",
                committed="focus:1.2m",
                draft=None,
                draftAppliedToCamera=False,
                draftSeparated=True,
                invalidPartial=False,
            )
        )
        self.assertEqual(result["decision"], "committed_preserved")
        self.assertEqual(result["preservedResults"], ["committed:focus:1.2m"])
        self.assertEqual(result["openQuestions"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unseparated_draft_is_rejected(self):
        result = evaluate(payload(recreation="rotation", draftSeparated=False, invalidPartial=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("draft-not-separated", result["rejectedClaims"])
        self.assertIn("committed:iso:400", result["preservedResults"])
        self.assertIn("draft:iso:4", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "recreation": "theme"},
            {**valid, "draft": None, "invalidPartial": True},
            {**valid, "committed": ""},
            {**valid, "draftAppliedToCamera": "no"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
