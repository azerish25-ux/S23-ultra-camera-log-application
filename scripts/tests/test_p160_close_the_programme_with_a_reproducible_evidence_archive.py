"""Host checks for P160. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p160_close_the_programme_with_a_reproducible_evidence_archive",
    Path(__file__).resolve().parents[1] / "gates" / "p160_close_the_programme_with_a_reproducible_evidence_archive.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P160_CLOSE_THE_PROGRAMME_WITH_A_REPRODUCIBLE_EVIDENCE_ARCHIVE.json").read_text(
            encoding="utf-8"
        )
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


class P160Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P160")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Close the programme with a reproducible evidence archive")
        self.assertEqual(
            _MODULE.GOAL,
            "Leave a maintainable application and an honest record of what the research established.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Archive source revisions, approved profiles, model identities, fixture rights, "
            "test commands, physical reports, known limitations, and deferred hypotheses. "
            "Preserve failed experiments that explain design decisions. The final claim set "
            "must be reproducible from evidence without relying on the original developer’s memory.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A new maintainer rebuilding the app and reproducing one capture, one film render, "
            "and one virtual-lens evaluation.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The archive provides enough information to reproduce qualified behaviour and clearly "
            "identifies unavailable physical prerequisites.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Delete unsuccessful experiments and publish only attractive final renders.",
        )
        self.assertEqual(
            _MODULE.DELIVERABLE,
            "Final research archive, maintenance guide, and evidence-bound roadmap",
        )
        self.assertEqual(_MODULE.DEPENDENCIES, ("P159",))
        self.assertIn("retained false", _MODULE.ARCHIVE_RULE)
        self.assertIn("not_run", _MODULE.ARCHIVE_RULE)
        self.assertIn("only_passes", _MODULE.ARCHIVE_RULE)
        self.assertIn("not established", _MODULE.ARCHIVE_RULE)
        self.assertEqual(_MODULE.DECISIONS, frozenset({"recorded", "rejected"}))
        self.assertNotIn("qualified", _MODULE.DECISIONS)
        self.assertNotIn("allowed", _MODULE.DECISIONS)

    def test_fixture_keeps_failed_and_not_run_records(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P160")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.ARCHIVE_RULE, " ".join(result["reasons"]))
        self.assertIn("not established", " ".join(result["openQuestions"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["failedRetained"], ["p010-route"])
        self.assertEqual(snapshot["notRunRetained"], ["physical-s23"])
        self.assertEqual(snapshot["failedDeleted"], [])
        self.assertTrue(snapshot["includesFailed"])
        self.assertTrue(snapshot["includesNotRun"])
        self.assertFalse(snapshot["onlyPasses"])
        self.assertTrue(snapshot["maintenanceNoteComplete"])
        self.assertEqual(
            snapshot["mustKeep"]["unestablished"],
            list(_MODULE.REQUIRED_UNESTABLISHED),
        )
        self.assertEqual(snapshot["mustKeep"]["failedExperiments"], ["p010-route"])
        self.assertEqual(snapshot["mustKeep"]["notRunRecords"], ["physical-s23"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_deleting_a_failed_experiment_is_rejected(self):
        result = assess(document(records=_MODULE.deleted_failed_records()))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.DELETED_FAILED, result["rejectedClaims"])
        self.assertIn(_MODULE.PASSES_ONLY, result["rejectedClaims"])
        self.assertNotIn(_MODULE.ONLY_ATTRACTIVE, result["rejectedClaims"])
        self.assertIn("p160-evidence-archive", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["failedDeleted"], ["p010-route"])
        self.assertFalse(result["preservedResults"][1]["includesFailed"])
        self.assertIn("deleting a failed experiment is rejected", " ".join(result["reasons"]))
        self.assertIn("p010-route", result["preservedResults"][1]["mustKeep"]["failedExperiments"])

    def test_passes_only_archive_is_rejected(self):
        result = assess(document(records=_MODULE.passes_only_records()))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PASSES_ONLY, result["rejectedClaims"])
        self.assertNotIn(_MODULE.DELETED_FAILED, result["rejectedClaims"])
        self.assertIn("failed and not_run", " ".join(result["reasons"]))
        self.assertIn("p160-evidence-archive", result["preservedResults"])
        kept_not_run = [
            row for row in _MODULE.fixture_records() if row["outcome"] != "not_run"
        ]
        missing_not_run = assess(document(records=kept_not_run))
        self.assertIn(_MODULE.PASSES_ONLY, missing_not_run["rejectedClaims"])
        self.assertTrue(missing_not_run["preservedResults"][1]["includesFailed"])
        self.assertFalse(missing_not_run["preservedResults"][1]["includesNotRun"])

    def test_only_passes_publication_is_rejected(self):
        result = assess(document(only_passes=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ONLY_ATTRACTIVE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.PASSES_ONLY, result["rejectedClaims"])
        self.assertNotIn(_MODULE.DELETED_FAILED, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["onlyPasses"])
        self.assertTrue(result["preservedResults"][1]["includesFailed"])
        self.assertIn("only attractive renders", " ".join(result["reasons"]))
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p160-evidence-archive", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_apply_mutant_deletes_failures_and_publishes_renders(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DELETED_FAILED, result["rejectedClaims"])
        self.assertIn(_MODULE.PASSES_ONLY, result["rejectedClaims"])
        self.assertIn(_MODULE.ONLY_ATTRACTIVE, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["failedDeleted"], ["p010-route"])
        self.assertTrue(result["preservedResults"][1]["onlyPasses"])
        self.assertIn("p160-evidence-archive", result["preservedResults"])

    def test_incomplete_maintenance_note_is_rejected(self):
        note = "physical S23 and sensor-derived Log are not established"
        result = assess(document(maintenanceNote=note))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOTE_INCOMPLETE, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["maintenanceNoteComplete"])
        self.assertIn("ten-bit fidelity", " ".join(result["reasons"]))
        self.assertIn("film-stock fidelity", " ".join(result["reasons"]))
        self.assertIn("cinema-camera equivalence", " ".join(result["reasons"]))
        established = assess(document(
            maintenanceNote=(
                "physical S23, sensor-derived Log, ten-bit fidelity, film-stock fidelity, "
                "and cinema-camera equivalence are established"
            )
        ))
        self.assertIn(_MODULE.NOTE_INCOMPLETE, established["rejectedClaims"])
        self.assertIn("p160-evidence-archive", result["preservedResults"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P161"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(only_passes="false"),
            document(extra=True),
            document(records=[]),
            document(records=[{"id": "a", "outcome": "passed", "retained": 1}]),
            document(records=[{"id": "a", "outcome": "skipped", "retained": True}]),
            document(records=[
                {"id": "a", "outcome": "failed", "retained": True},
                {"id": "a", "outcome": "not_run", "retained": True},
            ]),
            document(maintenanceNote="  "),
            {"records": _MODULE.fixture_records()},
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload) if isinstance(payload, dict) and (
                        "schemaVersion" in payload or payload == {} or not isinstance(payload, dict)
                    ) else evaluate(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(_MODULE.core_payload(only_passes=False, extra=True))

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P160-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P160")
        self.assertEqual(handoff["nextPhase"], "closed")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p160*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P160_CLOSE_THE_PROGRAMME_WITH_A_REPRODUCIBLE_EVIDENCE_ARCHIVE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Final research archive, maintenance guide, and evidence-bound roadmap", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("failed", note)
        self.assertIn("not_run", note)
        self.assertIn("only_passes", note)
        self.assertIn("retained", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("not established", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p160_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p160_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P160-0{index}")
            self.assertEqual(module.CASE["phase"], "P160")
            self.assertEqual(module.CASE["workstream"], 20)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
