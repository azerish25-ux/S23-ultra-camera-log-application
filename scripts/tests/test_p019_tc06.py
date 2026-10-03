"""TC-P019-06 draft control recreation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p019_tc06", Path(__file__).resolve().parents[1] / "gates" / "p019_tc06.py"
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
        "committed": {"iso": "100", "shutterNs": "33333333"},
        "draft": {"iso": "8"},
        "draftValid": False,
        "appliedToCamera": False,
    }
    base.update(overrides)
    return base


class TcP01906(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P019-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("unapplied or invalid control draft", _MODULE.INTERVENTION)
        self.assertIn("committed effective state", _MODULE.EXPECTED)
        self.assertIn("invalid partial numeric entry", _MODULE.NEGATIVE)
        self.assertIn("rotation", _MODULE.RECREATIONS)
        self.assertIn("manual_mode_transition", _MODULE.RECREATIONS)
        self.assertIn("cancelled_edits", _MODULE.RECREATIONS)

    def test_rotation_keeps_committed_exposure_apart_from_the_draft(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "draft_separated")
        self.assertEqual(
            result["preservedResults"],
            ["committed:iso=100", "committed:shutterNs=33333333"],
        )
        self.assertNotIn("committed:iso=8", result["preservedResults"])
        self.assertIn("invalid draft not applied", result["openQuestions"])

    def test_cancelled_edit_drops_a_valid_draft_without_applying_it(self):
        result = evaluate(
            payload(
                recreation="cancelled_edits",
                draft={"iso": "800"},
                draftValid=True,
            )
        )
        self.assertEqual(result["decision"], "draft_separated")
        self.assertIn("committed:iso=100", result["preservedResults"])
        self.assertTrue(any("cancelled edit dropped the draft" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_manual_mode_transition_without_a_draft_preserves_committed_state(self):
        result = evaluate(
            payload(recreation="manual_mode_transition", draft=None, draftValid=True)
        )
        self.assertEqual(result["decision"], "draft_separated")
        self.assertIn("committed:shutterNs=33333333", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["no draft to restore"])

    def test_invalid_partial_iso_reaching_the_camera_is_rejected(self):
        result = evaluate(payload(appliedToCamera=True, recreation="process_recreation"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["invalid-draft-applied"])
        self.assertIn("committed:iso=100", result["preservedResults"])
        self.assertNotIn("committed:iso=8", result["preservedResults"])
        self.assertTrue(any("must not reach the camera" in item for item in result["reasons"]))

    def test_valid_draft_applied_during_recreation_is_withheld(self):
        result = evaluate(
            payload(
                recreation="manual_mode_transition",
                draft={"iso": "800"},
                draftValid=True,
                appliedToCamera=True,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("draft-applied-on-recreation", result["rejectedClaims"])
        self.assertIn("committed:iso=100", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "recreation": "theme"},
            {**valid, "committed": {}},
            {**valid, "draft": None, "draftValid": False},
            {**valid, "draft": {"iso": ""}, "draftValid": True},
            {**valid, "appliedToCamera": "false"},
            {k: v for k, v in valid.items() if k != "recreation"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
