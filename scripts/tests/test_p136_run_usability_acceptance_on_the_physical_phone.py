"""Host checks for P136. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p136_run_usability_acceptance_on_the_physical_phone",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p136_run_usability_acceptance_on_the_physical_phone.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (
            _ROOT / "docs" / "P136_RUN_USABILITY_ACCEPTANCE_ON_THE_PHYSICAL_PHONE.json"
        ).read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def finding(**overrides):
    value = {
        "finding_id": "outdoor-readability",
        "claims_physical_pass": False,
        "measurement_id": None,
        "aesthetic_only": False,
    }
    value.update(overrides)
    return value


def report_view(result):
    return result["preservedResults"][1]


class P136Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P136")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.TITLE, "Run usability acceptance on the physical phone")
        self.assertEqual(_MODULE.SLUG, "run_usability_acceptance_on_the_physical_phone")
        self.assertEqual(
            _MODULE.GOAL,
            "Validate real shooting ergonomics rather than relying on static mockups.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Test outdoor readability, one-handed operation, landscape framing, gloves where relevant, "
            "large text, interruptions, and recovery discovery. Observe user tasks and errors. "
            "Keep aesthetic preferences separate from measurable task completion and footage safety.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A user starts a take, receives a thermal warning, stops, finds the retained clip, "
            "and shares its evidence.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The task completes without hidden controls or ambiguity about whether footage was saved.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Approve the UI from a desktop screenshot without a real shooting workflow.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Physical usability report and prioritized corrections")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P135",))
        self.assertEqual(_MODULE.OPEN_QUESTION, "physical S23 measurement was not run")

    def test_fixture_is_recorded_as_not_run(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(evaluate(source), result)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P136")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertIn("usability acceptance recorded as not run", result["reasons"])
        self.assertIn("shooting workflow result was not invented", result["reasons"])
        view = report_view(result)
        self.assertEqual(view["session_count"], 0)
        self.assertIsNone(view["device_id"])
        self.assertFalse(view["measured_on_device"])
        self.assertFalse(view["approved"])
        self.assertEqual(view["physical_sessions"], 0)
        self.assertEqual(view["findings"], [])
        self.assertEqual(view["status"], "not-run")
        self.assertIsNone(view["shootingWorkflow"])
        self.assertEqual(view["corrections"], [])
        self.assertEqual(_MODULE.physical_sessions(view), 0)

    def test_desktop_screenshot_approval_is_rejected(self):
        result = assess(document(approved=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertNotIn("usability acceptance recorded as not run", result["reasons"])
        view = report_view(result)
        self.assertTrue(view["approved"])
        self.assertFalse(view["measured_on_device"])
        self.assertEqual(view["physical_sessions"], 0)
        self.assertEqual(view["status"], "rejected")
        self.assertIsNone(view["shootingWorkflow"])
        self.assertIn("p136-usability", result["preservedResults"])
        self.assertTrue(view["corrections"])

    def test_desktop_sessions_are_not_physical_sessions(self):
        result = assess(document(session_count=3, device_id="desktop-preview"))
        self.assertEqual(result["decision"], "recorded")
        view = report_view(result)
        self.assertEqual(view["session_count"], 3)
        self.assertEqual(view["physical_sessions"], 0)
        self.assertEqual(view["status"], "not-run")
        self.assertIsNone(view["shootingWorkflow"])
        self.assertIn("physical_sessions is 0", " ".join(result["reasons"]))

    def test_physical_pass_without_measurement_id_is_rejected(self):
        result = assess(document(findings=[finding(claims_physical_pass=True)]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID, result["rejectedClaims"])
        self.assertIn(
            "findings that claim a physical pass without a device measurement id are rejected",
            result["reasons"],
        )
        view = report_view(result)
        self.assertIsNone(view["shootingWorkflow"])
        self.assertEqual(view["physical_sessions"], 0)
        self.assertIn("p136-usability", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_measurement_string_on_a_screenshot_is_not_a_device_measurement(self):
        result = assess(
            document(
                device_id="SM-S918B",
                findings=[
                    finding(
                        claims_physical_pass=True,
                        measurement_id="shot-001",
                    )
                ],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID, result["rejectedClaims"])
        self.assertNotIn(_MODULE.SHOOTING_WORKFLOW_NOT_OBSERVED, result["rejectedClaims"])
        self.assertIsNone(report_view(result)["shootingWorkflow"])
        self.assertEqual(report_view(result)["physical_sessions"], 0)

    def test_claimed_device_pass_does_not_invent_a_workflow(self):
        result = assess(
            document(
                session_count=1,
                device_id="SM-S918B",
                measured_on_device=True,
                approved=True,
                findings=[
                    finding(
                        claims_physical_pass=True,
                        measurement_id="shot-001",
                    )
                ],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.SHOOTING_WORKFLOW_NOT_OBSERVED, result["rejectedClaims"])
        self.assertIn(_MODULE.APPROVAL_WITHOUT_WORKFLOW, result["rejectedClaims"])
        self.assertNotIn(_MODULE.PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID, result["rejectedClaims"])
        self.assertNotIn(_MODULE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])
        view = report_view(result)
        self.assertIsNone(view["shootingWorkflow"])
        self.assertEqual(view["physical_sessions"], 1)
        self.assertEqual(view["status"], "rejected")
        self.assertIn("shooting workflow result was not invented", result["reasons"])

    def test_aesthetic_preference_cannot_be_a_task_pass(self):
        result = assess(
            document(
                findings=[
                    finding(
                        finding_id="grade-preference",
                        claims_physical_pass=True,
                        aesthetic_only=True,
                    )
                ]
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.AESTHETIC_AS_TASK, result["rejectedClaims"])
        self.assertIn(_MODULE.PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID, result["rejectedClaims"])
        self.assertIsNone(report_view(result)["shootingWorkflow"])

    def test_aesthetic_note_without_a_pass_stays_not_run(self):
        result = assess(
            document(
                findings=[
                    finding(
                        finding_id="grade-preference",
                        claims_physical_pass=False,
                        aesthetic_only=True,
                    )
                ]
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(report_view(result)["status"], "not-run")
        self.assertTrue(report_view(result)["findings"][0]["aesthetic_only"])
        self.assertIsNone(report_view(result)["shootingWorkflow"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess([])
        with self.assertRaises(ValueError):
            evaluate(document(applyNegative=True))
        with self.assertRaises(ValueError):
            assess(document(session_count=True))
        with self.assertRaises(ValueError):
            assess(document(session_count=-1))
        with self.assertRaises(ValueError):
            assess(document(measured_on_device=0))
        with self.assertRaises(ValueError):
            assess(document(approved="true"))
        with self.assertRaises(ValueError):
            assess(document(device_id=""))
        with self.assertRaises(ValueError):
            assess(document(phase="P135"))
        with self.assertRaises(ValueError):
            assess(document(implementationBaseRevision="deadbeef"))
        with self.assertRaises(ValueError):
            assess(document(schemaVersion=1.0))
        with self.assertRaises(ValueError):
            assess(document(findings=[{"finding_id": "x"}]))
        with self.assertRaises(ValueError):
            assess(document(findings=[finding(measurement_id="")]))
        with self.assertRaises(ValueError):
            assess(document(findings=[finding(), finding()]))
