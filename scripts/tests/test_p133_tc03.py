"""Tests for TC-P133-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p133-tc03",
        "repeat": "focus distance",
        "controls": _GATE.fixture_controls(),
        "focusOrder": _GATE.fixture_focus_order(),
        "controlId": "virtual-focus",
        "committedState": "changed",
        "draftText": "1.",
        "draftApplied": False,
        "draftMinimum": 0.3,
        "draftMaximum": 10,
    }
    base.update(overrides)
    return base


class TCP13303(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_draft_stays_unapplied(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["draftKind"], "incomplete")
        self.assertTrue(result["preservedResults"][2]["draftVisibleUnapplied"])
        self.assertEqual(result["preservedResults"][2]["spokenState"], "changed")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "partial-draft-reached-camera")

    def test_partial_text_that_reaches_the_camera_is_rejected(self):
        result = evaluate(payload(draftApplied=True, repeat="ISO"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["spokenState"], "changed")
        self.assertIn("p133-tc03", result["preservedResults"])

    def test_out_of_range_value_is_rejected_and_committed_state_remains(self):
        result = evaluate(payload(draftText="99", draftApplied=True, repeat="ROI coordinates"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OUT_OF_RANGE, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["spokenState"], "changed")
        self.assertEqual(result["preservedResults"][2]["committedState"], "changed")

    def test_in_range_apply_can_replace_the_spoken_value(self):
        controls = _GATE.replace_control(
            _GATE.fixture_controls(), "virtual-focus", state_description="2.8"
        )
        result = evaluate(payload(controls=controls, draftText="2.8", draftApplied=True, repeat="shutter"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["spokenState"], "2.8")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(controlId="missing-control"))
        with self.assertRaises(ValueError):
            evaluate(payload(draftMinimum=10, draftMaximum=0.3))
