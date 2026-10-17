"""Tests for TC-P136-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc03",
        "repeat": "shutter",
        "report": _GATE.honest_report(),
        "control": "shutter",
        "committed": 180,
        "draft": "180",
        "minimum": 1,
        "maximum": 8000,
        "interruptedBeforeApply": False,
        "reachedCamera": True,
        "draftVisible": True,
    }
    base.update(overrides)
    return base


class TCP13603(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Invalid control draft")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Enter an incomplete or out-of-range numeric value and interrupt editing before Apply.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Preserve committed settings and keep the draft visibly unapplied or invalid.",
        )
        self.assertEqual(_MODULE.CASE["negative"], "Partially typed input reaching the camera must fail.")
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat shutter, ISO, focus distance, ROI coordinates, and output dimensions.",
        )

    def test_complete_in_range_draft_is_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        view = result["preservedResults"][2]
        self.assertEqual(view["committed"], 180)
        self.assertEqual(view["draftKind"], "complete")
        self.assertEqual(view["appliedValue"], 180)
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")

    def test_partial_draft_reaching_the_camera_is_rejected(self):
        result = evaluate(payload(draft="18.", interruptedBeforeApply=True, reachedCamera=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["committed"], 180)
        self.assertEqual(result["preservedResults"][2]["draftKind"], "incomplete")
        self.assertEqual(result["preservedResults"][2]["appliedValue"], 180)
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_out_of_range_and_hidden_drafts_are_rejected(self):
        out_of_range = evaluate(payload(control="iso", draft="99999", reachedCamera=True))
        self.assertEqual(out_of_range["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, out_of_range["rejectedClaims"])
        self.assertEqual(out_of_range["preservedResults"][2]["draftKind"], "out-of-range")
        hidden = evaluate(payload(control="focus-distance", draft="1e", reachedCamera=False, draftVisible=False))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn(_MODULE.DRAFT_HIDDEN, hidden["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, hidden["rejectedClaims"])

    def test_interrupted_valid_draft_must_not_reach_the_camera(self):
        result = evaluate(payload(interruptedBeforeApply=True, reachedCamera=True, draftVisible=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["committed"], 180)

    def test_screenshot_approval_is_rejected(self):
        result = evaluate(payload(report=_GATE.honest_report(approved=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc03-roi"
        result = evaluate(payload(evidenceId=evidence, repeat="roi", control="roi", committed=0.2, draft="0.2", minimum=0, maximum=1))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(control="kelvin"))
        with self.assertRaises(ValueError):
            evaluate(payload(minimum=5, maximum=5))
        with self.assertRaises(ValueError):
            evaluate(payload(draft=18))
