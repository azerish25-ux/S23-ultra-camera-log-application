"""TC-P022-06 recreation keeps committed control apart from the draft."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc06", Path(__file__).resolve().parents[1] / "gates" / "p022_tc06.py"
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
_HASH = "cm-draft"


def payload(**overrides):
    base = {
        "event": "rotation",
        "committedControl": "iso",
        "committedValue": "200",
        "draftValue": "400",
        "draftValid": True,
        "appliedToSensor": False,
        "cleanMasterHash": _HASH,
    }
    base.update(overrides)
    return base


class TcP02206(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("unapplied or invalid", _MODULE.INTERVENTION)
        self.assertIn("committed effective state", _MODULE.EXPECTED)
        self.assertIn("partial numeric", _MODULE.NEGATIVE)

    def test_rotation_keeps_committed_iso_and_labels_the_draft(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["preservedResults"], ["iso=200", "draft-unapplied:400", _HASH])
        self.assertTrue(any("rotation" in item for item in result["reasons"]))
        self.assertNotIn("iso=400", result["preservedResults"])

    def test_process_recreation_also_separates_the_draft(self):
        result = evaluate(payload(event="process_recreation", draftValue="250"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["preservedResults"], ["iso=200", "draft-unapplied:250", _HASH])
        self.assertTrue(any("process_recreation" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_partial_numeric_reaching_the_camera_is_rejected(self):
        result = evaluate(
            payload(event="manual_mode_transition", draftValue="40.", draftValid=False, appliedToSensor=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "separated"})
        self.assertEqual(result["rejectedClaims"], ["invalid-draft-reached-camera"])
        self.assertEqual(result["preservedResults"], ["iso=200", _HASH])
        self.assertNotIn("40.", result["preservedResults"])

    def test_lying_about_a_partial_entry_still_fails(self):
        result = evaluate(payload(draftValue="40.", draftValid=True, appliedToSensor=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invalid-draft-reached-camera", result["rejectedClaims"])
        self.assertIn("iso=200", result["preservedResults"])
        self.assertIn(_HASH, result["preservedResults"])

    def test_partial_entry_that_does_not_reach_the_camera_stays_separated(self):
        result = evaluate(payload(draftValue="40.", draftValid=False, appliedToSensor=False))
        self.assertEqual(result["decision"], "separated")
        self.assertIn("draft-unapplied:40.", result["preservedResults"])
        self.assertEqual(result["preservedResults"][0], "iso=200")

    def test_cancelled_edit_discards_the_draft_and_keeps_the_commit(self):
        result = evaluate(payload(event="cancelled_edit"))
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["preservedResults"], ["iso=200", _HASH])
        self.assertNotIn("400", " ".join(result["preservedResults"]))
        self.assertTrue(any("discarded" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "event": "scroll"},
            {**valid, "draftValue": None, "draftValid": False},
            {**valid, "appliedToSensor": "no"},
            {**valid, "committedValue": ""},
            {k: v for k, v in valid.items() if k != "event"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
