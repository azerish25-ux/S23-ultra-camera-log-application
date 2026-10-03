"""TC-P021-06 draft control recreation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc06", Path(__file__).resolve().parents[1] / "gates" / "p021_tc06.py"
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
        "event": "rotation",
        "committedSubject": "nearby_foreground",
        "committedDistance": "unknown",
        "draft": "0.",
        "draftValid": False,
        "reachesCamera": False,
    }
    base.update(overrides)
    return base


class TcP02106(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _MODULE.FOCUS_INVENTORY:
            self.assertIn(token, result["preservedResults"])
        self.assertIn("applied.subject:nearby_foreground", result["preservedResults"])
        self.assertIn("applied.distance:unknown", result["preservedResults"])

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("unapplied or invalid control draft", _MODULE.INTERVENTION)
        self.assertIn("separate any restored draft", _MODULE.EXPECTED)
        self.assertIn("invalid partial numeric entry", _MODULE.NEGATIVE)
        for name in ("rotation", "process_recreation", "manual_mode_transition", "cancelled_edits"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_repeat_rotation_keeps_draft_unapplied(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "draft_separated")
        self.assertIn("draft.unapplied:0.", result["preservedResults"])
        self.assertNotIn("applied.distance:0.", result["preservedResults"])
        self.assertTrue(any("rotation" in item for item in result["reasons"]))

    def test_repeat_process_recreation_separates_draft(self):
        result = evaluate(payload(event="process_recreation", draft="1.2", draftValid=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "draft_separated")
        self.assertIn("draft.unapplied:1.2", result["preservedResults"])
        self.assertIn("applied.distance:unknown", result["preservedResults"])
        self.assertNotIn("applied.distance:1.2", result["preservedResults"])

    def test_repeat_manual_transition_and_cancelled_edits(self):
        manual = evaluate(payload(event="manual_mode_transition", draft="9", draftValid=False))
        cancelled = evaluate(payload(event="cancelled_edits", draft="3.", draftValid=False))
        self.assertEqual(manual["decision"], "draft_separated")
        self.assertEqual(cancelled["decision"], "draft_separated")
        self.assertIn("draft.unapplied:9", manual["preservedResults"])
        self.assertIn("draft.unapplied:3.", cancelled["preservedResults"])
        self.assertTrue(any("cancelled edit" in item for item in cancelled["reasons"]))
        self.assertIn("physical.distance:unknown", cancelled["preservedResults"])

    def test_negative_invalid_partial_entry_does_not_reach_camera(self):
        result = evaluate(payload(reachesCamera=True, draft="0.", draftValid=False, event="rotation"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "draft_separated"})
        self.assertIn("invalid-draft-reached-camera", result["rejectedClaims"])
        self.assertNotIn("draft.unapplied:0.", result["preservedResults"])
        self.assertNotIn("applied.distance:0.", result["preservedResults"])
        self.assertIn("applied.distance:unknown", result["preservedResults"])
        self.assertIn("virtual.subject:face", result["preservedResults"])

    def test_negative_on_manual_transition_preserves_committed_distance(self):
        result = evaluate(
            payload(event="manual_mode_transition", reachesCamera=True, draftValid=False, draft="12")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("applied.distance:unknown", result["preservedResults"])
        self.assertNotIn("applied.distance:12", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "event": "resize"},
            {**valid, "draft": ""},
            {**valid, "draftValid": "no"},
            {**valid, "reachesCamera": None},
            {**valid, "extra": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
