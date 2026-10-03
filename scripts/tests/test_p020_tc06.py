"""TC-P020-06 host checks. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc06", Path(__file__).resolve().parents[1] / "gates" / "p020_tc06.py"
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
_INVENTORY = _MODULE.WB_INVENTORY


def _contract(test, result):
    test.assertEqual(tuple(result), _KEYS)
    test.assertEqual(result["caseId"], "TC-P020-06")
    test.assertNotIn(result["decision"], {"qualified", "allowed"})
    test.assertIsInstance(result["reasons"], list)
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
    for key in ("rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) for item in result[key]))


def _inventory(test, result):
    for item in _INVENTORY:
        test.assertIn(item, result["preservedResults"])


def payload(**overrides):
    base = {
        "event": "rotation",
        "committedPreset": "daylight",
        "committedGains": "1.42,1.00,1.78",
        "draft": "3.",
        "draftValid": False,
        "reachesCamera": False,
    }
    base.update(overrides)
    return base


class TcP02006(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertIn("control draft", _MODULE.INTERVENTION)
        self.assertIn("applied sensor control", _MODULE.EXPECTED)
        self.assertIn("partial numeric", _MODULE.NEGATIVE)
        for name in ("rotation", "process_recreation", "manual_mode_transition", "cancelled_edits"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_rotation_keeps_committed_state_apart_from_the_draft(self):
        result = evaluate(payload())
        _contract(self, result)
        self.assertEqual(result["decision"], "draft_separated")
        self.assertIn("applied.preset:daylight", result["preservedResults"])
        self.assertIn("applied.gains:1.42,1.00,1.78", result["preservedResults"])
        self.assertIn("draft.unapplied:3.", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("rotation" in item for item in result["reasons"]))

    def test_cancelled_edits_stay_unapplied(self):
        result = evaluate(payload(event="cancelled_edits", draft="4500", draftValid=True))
        _contract(self, result)
        self.assertEqual(result["decision"], "draft_separated")
        self.assertIn("draft.unapplied:4500", result["preservedResults"])
        self.assertIn("applied.preset:daylight", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("cancelled" in item for item in result["reasons"]))

    def test_invalid_partial_entry_reaching_the_camera_is_rejected(self):
        result = evaluate(payload(event="manual_mode_transition", draft="32", reachesCamera=True))
        _contract(self, result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "draft_separated"})
        self.assertEqual(result["rejectedClaims"], ["invalid-draft-reached-camera"])
        self.assertNotIn("draft.unapplied:32", result["preservedResults"])
        self.assertIn("applied.gains:1.42,1.00,1.78", result["preservedResults"])
        _inventory(self, result)

    def test_process_recreation_does_not_apply_a_valid_unsent_draft(self):
        result = evaluate(payload(event="process_recreation", draft="cloudy", draftValid=True, reachesCamera=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unapplied-draft-reached-camera", result["rejectedClaims"])
        self.assertIn("applied.preset:daylight", result["preservedResults"])
        _inventory(self, result)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [None, {**valid, "event": "reboot"}, {**valid, "draftValid": "no"}]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
