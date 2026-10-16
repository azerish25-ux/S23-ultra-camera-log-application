"""Host checks for P123. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_implement_the_development_job_state_machine",
    Path(__file__).resolve().parents[1] / "gates" / "p123_implement_the_development_job_state_machine.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE

_ROOT = Path(__file__).resolve().parents[2]
_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
_LEGAL = {
    ("idle", "queued"),
    ("queued", "running"),
    ("running", "checkpointed"),
    ("checkpointed", "running"),
    ("running", "completed"),
    ("running", "failed"),
    ("running", "cancelled"),
    ("queued", "cancelled"),
    ("checkpointed", "cancelled"),
    ("checkpointed", "failed"),
}


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P123",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p123-cancel-during-verification",
        "claim": "synthetic-host-fixture",
        "transitionLog": ["idle", "queued", "running", "cancelled"],
        "terminalState": "cancelled",
        "sourceRetained": True,
        "workersReleased": True,
        "stalePublish": False,
        "applyMutant": False,
    }
    value.update(overrides)
    return value


def job(**overrides):
    value = {
        "caseId": "P123",
        "evidenceId": "p123-evaluate",
        "claim": "synthetic-host-fixture",
        "transitionLog": ["idle", "queued", "running", "completed"],
        "terminalState": "completed",
        "sourceRetained": True,
        "workersReleased": True,
        "stalePublish": False,
        "applyMutant": False,
    }
    value.update(overrides)
    return value


class P123Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P123")
        self.assertEqual(_MODULE.TITLE, "Implement the development job state machine")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P122",))
        self.assertEqual(
            _MODULE.GOAL,
            "Make queued, preparing, rendering, verifying, publishing, cancelled, and failed states explicit.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Own jobs independently of the screen while respecting Android execution policy. "
            "Record resource requirements, current phase, progress confidence, and failure reason. "
            "Cancellation is acknowledged only after workers release ownership and retain appropriate partial artifacts.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "Cancellation during output verification followed by reopening the development screen.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The job state is consistent, source media remains intact, and a stale worker cannot publish a cancelled result.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Mark cancellation complete immediately while background workers still own output handles.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Job reducer and cancellation race tests")
        self.assertEqual(_MODULE.LEGAL_STATES, frozenset(_MODULE.LEGAL_STATE_ORDER))
        self.assertEqual(
            _MODULE.LEGAL_STATE_ORDER,
            ("idle", "queued", "running", "checkpointed", "failed", "cancelled", "completed"),
        )
        self.assertEqual(_MODULE.LEGAL_TRANSITIONS, frozenset(_LEGAL))
        self.assertEqual(set(_MODULE.LEGAL_TRANSITION_LIST), _LEGAL)
        self.assertEqual(len(_MODULE.LEGAL_TRANSITION_LIST), len(_LEGAL))

    def test_cancellation_fixture_is_recorded(self):
        result = assess(document())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "P123")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p123-cancel-during-verification", result["preservedResults"])
        self.assertIn(["idle", "queued", "running", "cancelled"], result["preservedResults"])
        self.assertIn("cancelled", result["preservedResults"])
        self.assertIn(True, result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertEqual(result["preservedResults"][5]["workersReleased"], True)
        self.assertEqual(result["preservedResults"][5]["illegalTransitions"], [])

    def test_fixture_file_and_handoff(self):
        payload = json.loads(
            (_ROOT / "docs" / "P123_IMPLEMENT_THE_DEVELOPMENT_JOB_STATE_MACHINE.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2], ["idle", "queued", "running", "cancelled"])
        self.assertEqual(result["preservedResults"][4], True)
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P123-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P123")
        self.assertEqual(handoff["nextPhase"], "P124")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p123*.py' -v",
        )
        self.assertEqual(len(handoff["caseIds"]), 8)
        note = (_ROOT / "docs" / "P123_IMPLEMENT_THE_DEVELOPMENT_JOB_STATE_MACHINE.md").read_text()
        self.assertIn("python3 -m unittest discover -s scripts/tests -p 'test_p123*.py' -v", note)
        self.assertIn("idle->queued", note)
        self.assertIn("queued->completed", note)

    def test_completed_path_and_checkpoint_cycle_are_recorded(self):
        completed = assess(
            document(
                evidenceId="p123-completed",
                transitionLog=["idle", "queued", "running", "completed"],
                terminalState="completed",
                sourceRetained=False,
            )
        )
        self.assertEqual(completed["decision"], "recorded")
        self.assertEqual(completed["preservedResults"][4], False)
        cycle = assess(
            document(
                evidenceId="p123-cycle",
                transitionLog=["idle", "queued", "running", "checkpointed", "running", "completed"],
                terminalState="completed",
            )
        )
        self.assertEqual(cycle["decision"], "recorded")
        self.assertEqual(cycle["rejectedClaims"], [])

    def test_skipping_queued_to_completed_is_rejected(self):
        result = assess(
            document(
                transitionLog=["idle", "queued", "completed"],
                terminalState="completed",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("skipped-queued-to-completed", result["rejectedClaims"])
        self.assertIn("illegal-transition", result["rejectedClaims"])
        self.assertIn("p123-cancel-during-verification", result["preservedResults"])
        self.assertIn(["queued", "completed"], result["preservedResults"][5]["illegalTransitions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_other_illegal_transitions_are_rejected(self):
        result = assess(document(transitionLog=["idle", "running"], terminalState="running"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("illegal-transition", result["rejectedClaims"])
        self.assertNotIn("skipped-queued-to-completed", result["rejectedClaims"])
        stale = assess(
            document(
                transitionLog=["idle", "queued", "running", "cancelled", "completed"],
                terminalState="completed",
            )
        )
        self.assertEqual(stale["decision"], "rejected")
        self.assertIn("illegal-transition", stale["rejectedClaims"])
        self.assertIn(["cancelled", "completed"], stale["preservedResults"][5]["illegalTransitions"])

    def test_terminal_mismatch_is_rejected(self):
        result = assess(
            document(
                transitionLog=["idle", "queued", "running"],
                terminalState="completed",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("terminal-state-mismatch", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2], ["idle", "queued", "running"])
        self.assertEqual(result["preservedResults"][3], "completed")

    def test_cancel_without_source_retained_is_rejected(self):
        for log in (
            ["idle", "queued", "running", "cancelled"],
            ["idle", "queued", "cancelled"],
            ["idle", "queued", "running", "checkpointed", "cancelled"],
        ):
            result = assess(document(transitionLog=log, terminalState="cancelled", sourceRetained=False))
            self.assertEqual(result["decision"], "rejected", log)
            self.assertIn("source-not-retained-on-cancel", result["rejectedClaims"])
            self.assertIn("p123-cancel-during-verification", result["preservedResults"])
            self.assertIs(result["preservedResults"][4], False)

    def test_failure_does_not_delete_the_source(self):
        deleted = assess(
            document(
                evidenceId="p123-failed",
                transitionLog=["idle", "queued", "running", "failed"],
                terminalState="failed",
                sourceRetained=False,
            )
        )
        self.assertEqual(deleted["decision"], "rejected")
        self.assertIn("source-deleted-on-failure", deleted["rejectedClaims"])
        self.assertIn("p123-failed", deleted["preservedResults"])
        self.assertIs(deleted["preservedResults"][4], False)
        kept = assess(
            document(
                evidenceId="p123-failed-kept",
                transitionLog=["idle", "queued", "running", "checkpointed", "failed"],
                terminalState="failed",
                sourceRetained=True,
            )
        )
        self.assertEqual(kept["decision"], "recorded")
        self.assertEqual(kept["rejectedClaims"], [])
        self.assertIs(kept["preservedResults"][4], True)

    def test_workers_and_stale_publish_and_mutant(self):
        owned = assess(document(workersReleased=False))
        self.assertEqual(owned["decision"], "rejected")
        self.assertIn("workers-still-own-output-handles", owned["rejectedClaims"])
        self.assertIn("p123-cancel-during-verification", owned["preservedResults"])
        stale = assess(document(stalePublish=True))
        self.assertEqual(stale["decision"], "rejected")
        self.assertIn("stale-worker-published-cancelled-result", stale["rejectedClaims"])
        mutant = assess(document(applyMutant=True))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn(MUTANT, mutant["rejectedClaims"])
        self.assertIn(["idle", "queued", "running", "cancelled"], mutant["preservedResults"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed"})

    def test_evaluate_uses_the_same_reducer(self):
        result = evaluate(job())
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P123")
        self.assertEqual(result["preservedResults"][2], ["idle", "queued", "running", "completed"])
        self.assertIn("p123-evaluate", result["preservedResults"])
        queued_cancel = evaluate(
            job(
                caseId="TC-P123-04",
                evidenceId="p123-queued-cancel",
                transitionLog=["idle", "queued", "cancelled"],
                terminalState="cancelled",
            )
        )
        self.assertEqual(queued_cancel["decision"], "recorded")
        self.assertEqual(queued_cancel["caseId"], "TC-P123-04")

    def test_unknown_state_names_raise(self):
        for name in ("preparing", "rendering", "verifying", "publishing", "Idle", ""):
            with self.assertRaises(ValueError):
                assess(document(transitionLog=["idle", name], terminalState="idle"))
            with self.assertRaises(ValueError):
                assess(document(terminalState=name))
        with self.assertRaises(ValueError):
            assess(document(transitionLog=[], terminalState="idle"))
        with self.assertRaises(ValueError):
            assess(document(sourceRetained="true"))
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate({})
