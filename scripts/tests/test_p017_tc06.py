"""TC-P017-06 draft control recreation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc06", Path(__file__).resolve().parents[1] / "gates" / "p017_tc06.py"
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
_COMMITTED = "iso=200"


def payload(**overrides):
    base = {
        "recreation": "rotation",
        "committedEffective": _COMMITTED,
        "draft": "1.",
        "draftInvalid": True,
        "reachesCamera": False,
    }
    base.update(overrides)
    return base


class TcP01706(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("unapplied or invalid", _MODULE.INTERVENTION)
        self.assertIn("committed effective", _MODULE.EXPECTED)
        self.assertIn("partial numeric", _MODULE.NEGATIVE)
        self.assertIn("process_recreation", _MODULE.RECREATIONS)
        self.assertIn("cancelled_edits", _MODULE.RECREATIONS)

    def test_rotation_keeps_committed_and_separates_invalid_draft(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["preservedResults"], [_COMMITTED])
        self.assertNotIn("1.", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], ["draft-not-applied"])
        self.assertTrue(any("rotation" in item for item in result["reasons"]))
        self.assertTrue(any("separate from applied sensor control" in item for item in result["reasons"]))

    def test_process_recreation_preserves_committed_state(self):
        result = evaluate(
            payload(recreation="process_recreation", draft="iso=250", draftInvalid=False)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["preservedResults"], [_COMMITTED])
        self.assertNotIn("iso=250", result["preservedResults"])
        self.assertTrue(any("process_recreation" in item for item in result["reasons"]))

    def test_manual_mode_transition_does_not_apply_draft(self):
        result = evaluate(payload(recreation="manual_mode_transition", draft="9", draftInvalid=True))
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["preservedResults"], [_COMMITTED])
        self.assertNotIn("9", result["preservedResults"])

    def test_cancelled_edits_are_not_applied(self):
        result = evaluate(
            payload(recreation="cancelled_edits", draft="", draftInvalid=False, reachesCamera=False)
        )
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["preservedResults"], [_COMMITTED])
        self.assertTrue(any("cancelled draft is not applied" in item for item in result["reasons"]))
        self.assertEqual(result["openQuestions"], [])

    def test_invalid_partial_reaching_camera_is_rejected(self):
        result = evaluate(payload(reachesCamera=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["invalid-partial-entry"])
        self.assertEqual(result["preservedResults"], [_COMMITTED])
        self.assertNotIn("1.", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_entry_on_manual_transition_still_preserves_committed(self):
        result = evaluate(payload(recreation="manual_mode_transition", reachesCamera=True, draft="0."))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"], [_COMMITTED])
        self.assertNotIn("0.", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "recreation": "theme"},
            {**valid, "committedEffective": ""},
            {**valid, "draft": " 1."},
            {**valid, "draft": _COMMITTED, "draftInvalid": True},
            {**valid, "reachesCamera": "yes"},
            {k: v for k, v in valid.items() if k != "draft"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
