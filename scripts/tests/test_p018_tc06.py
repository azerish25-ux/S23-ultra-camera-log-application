"""TC-P018-06 draft control recreation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p018_tc06", Path(__file__).resolve().parents[1] / "gates" / "p018_tc06.py"
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
        "committed": {"iso": "400", "shutter": "1/48"},
        "draft": {"iso": "800"},
        "draftValid": True,
        "appliedToCamera": False,
    }
    base.update(overrides)
    return base


class TcP01806(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P018-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_contract(self):
        self.assertIn("unapplied or invalid control draft", _MODULE.INTERVENTION)
        self.assertIn("separate any restored draft", _MODULE.EXPECTED)
        self.assertIn("invalid partial numeric entry", _MODULE.NEGATIVE)
        self.assertIn("rotation", _MODULE.REPEAT)
        self.assertIn("cancelled edits", _MODULE.REPEAT)

    def test_rotation_keeps_committed_controls_apart_from_the_draft(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "draft_separated")
        self.assertEqual(
            result["preservedResults"],
            ["committed:iso=400", "committed:shutter=1/48"],
        )
        self.assertNotIn("committed:iso=800", result["preservedResults"])
        self.assertNotIn("800", " ".join(result["preservedResults"]))
        self.assertTrue(any("separate" in item for item in result["reasons"]))

    def test_cancelled_edit_drops_an_invalid_draft(self):
        result = evaluate(
            payload(
                recreation="cancelled_edits",
                draft={"iso": ""},
                draftValid=False,
                appliedToCamera=False,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "draft_separated")
        self.assertIn("committed:iso=400", result["preservedResults"])
        self.assertIn("committed:shutter=1/48", result["preservedResults"])
        self.assertIn("invalid draft not applied", result["openQuestions"])
        self.assertTrue(any("cancelled edit" in item for item in result["reasons"]))

    def test_process_recreation_and_manual_mode_keep_committed_state(self):
        for recreation in ("process_recreation", "manual_mode_transition"):
            result = evaluate(payload(recreation=recreation, draft=None, draftValid=True))
            with self.subTest(recreation=recreation):
                self.assertEqual(result["decision"], "draft_separated")
                self.assertIn("committed:iso=400", result["preservedResults"])
                self.assertIn("no draft to restore", result["openQuestions"])

    def test_invalid_partial_entry_reaching_the_camera_is_rejected(self):
        result = evaluate(
            payload(
                recreation="manual_mode_transition",
                draft={"shutter": "12."},
                draftValid=False,
                appliedToCamera=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["invalid-draft-applied"])
        self.assertIn("committed:iso=400", result["preservedResults"])
        self.assertIn("committed:shutter=1/48", result["preservedResults"])
        self.assertNotIn("committed:shutter=12.", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "recreation": "resize"},
            {**valid, "committed": {}},
            {**valid, "draft": None, "draftValid": False},
            {**valid, "draft": {"iso": ""}, "draftValid": True},
            {**valid, "appliedToCamera": "false"},
            {k: v for k, v in valid.items() if k != "committed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
