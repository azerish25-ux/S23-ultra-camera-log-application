"""Tests for TC-P136-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc08",
        "repeat": "one-handed",
        "report": _GATE.honest_report(),
        "event": "thermal",
        "footageSavedKnown": False,
        "nextActionKnown": False,
        "hiddenState": False,
        "desktopMockupSubstituted": False,
        "workflowObserved": False,
    }
    base.update(overrides)
    return base


class TCP13608(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Real shooting interruption")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Perform the task on the physical phone with a thermal warning, permission issue, or recovery event.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Let the user understand what was saved and complete the appropriate next action without hidden state.",
        )
        self.assertEqual(
            _MODULE.CASE["negative"],
            "A desktop mockup cannot substitute for observed physical task completion.",
        )
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat one-handed operation, outdoor visibility, and finding an interrupted take.",
        )

    def test_unobserved_interruption_is_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("usability acceptance recorded as not run", result["reasons"])
        self.assertIn("shooting workflow result was not invented", result["reasons"])
        view = result["preservedResults"][2]
        self.assertEqual(view["plannedEvent"], "thermal")
        self.assertFalse(view["workflowObserved"])
        self.assertFalse(view["footageSavedKnown"])
        self.assertIsNone(view["shootingWorkflow"])
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")
        self.assertEqual(result["preservedResults"][1]["physical_sessions"], 0)
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_desktop_mockup_is_rejected(self):
        result = evaluate(payload(desktopMockupSubstituted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIsNone(result["preservedResults"][2]["shootingWorkflow"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invented_workflow_and_hidden_state_are_rejected(self):
        invented = evaluate(payload(workflowObserved=True, footageSavedKnown=True, nextActionKnown=True))
        self.assertEqual(invented["decision"], "rejected")
        self.assertIn(_MODULE.INVENTED_WORKFLOW, invented["rejectedClaims"])
        self.assertNotIn(_MODULE.FOOTAGE_WITHOUT_WORKFLOW, invented["rejectedClaims"])
        self.assertIsNone(invented["preservedResults"][2]["shootingWorkflow"])
        hidden = evaluate(payload(event="permission", hiddenState=True))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_STATE, hidden["rejectedClaims"])
        claimed = evaluate(payload(event="recovery", footageSavedKnown=True))
        self.assertEqual(claimed["decision"], "rejected")
        self.assertIn(_MODULE.FOOTAGE_WITHOUT_WORKFLOW, claimed["rejectedClaims"])

    def test_physical_pass_finding_without_measurement_id_is_rejected(self):
        report = _GATE.honest_report(
            findings=[
                {
                    "finding_id": "interrupted-take",
                    "claims_physical_pass": True,
                    "measurement_id": None,
                    "aesthetic_only": False,
                }
            ]
        )
        result = evaluate(payload(report=report))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID, result["rejectedClaims"])
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_screenshot_approval_is_rejected(self):
        result = evaluate(payload(report=_GATE.honest_report(approved=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])
        self.assertIn(_GATE.MUTANT, result["reasons"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc08-outdoor"
        result = evaluate(payload(evidenceId=evidence, repeat="outdoor", event="recovery"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(event="battery"))
        with self.assertRaises(ValueError):
            evaluate(payload(workflowObserved="yes"))
