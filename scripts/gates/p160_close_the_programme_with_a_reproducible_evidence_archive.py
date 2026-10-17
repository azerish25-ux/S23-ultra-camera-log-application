#!/usr/bin/env python3
"""P160 Close the programme with a reproducible evidence archive.

Host reference only. This module does not probe a device and does not qualify
a physical S23. An archive lists records with id, outcome (passed, failed, or
not_run), and retained. Deleting a failed experiment (retained false for
outcome failed) is rejected. The archive must include failed and not_run
records, not only passes. A maintenance note must state that physical S23,
sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera
equivalence are not established. Publishing only attractive renders
(only_passes true) is rejected. The decision is recorded or rejected, never
qualified or allowed. Retention, outcomes, the maintenance note, and only_passes
are the evidence.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P160"
WORKSTREAM = 20
TITLE = "Close the programme with a reproducible evidence archive"
GOAL = "Leave a maintainable application and an honest record of what the research established."
METHOD = (
    "Archive source revisions, approved profiles, model identities, fixture rights, "
    "test commands, physical reports, known limitations, and deferred hypotheses. "
    "Preserve failed experiments that explain design decisions. The final claim set "
    "must be reproducible from evidence without relying on the original developer’s memory."
)
FIXTURE = (
    "A new maintainer rebuilding the app and reproducing one capture, one film render, "
    "and one virtual-lens evaluation."
)
ORACLE = (
    "The archive provides enough information to reproduce qualified behaviour and clearly "
    "identifies unavailable physical prerequisites."
)
MUTANT = "Delete unsuccessful experiments and publish only attractive final renders."
DELIVERABLE = "Final research archive, maintenance guide, and evidence-bound roadmap"
DEPENDENCIES = ("P159",)

ARCHIVE_RULE = (
    "An archive record has id, outcome passed|failed|not_run, and retained. "
    "retained false on outcome failed deletes a failed experiment and is rejected. "
    "The archive must include failed and not_run records, not only passes. "
    "The maintenance note must state that physical S23, sensor-derived Log, "
    "ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not established. "
    "only_passes true publishes only attractive renders and is rejected. "
    "The decision is never qualified or allowed."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p160-evidence-archive"
CLAIM = "reproducible-evidence-archive-host-reference"

OUTCOMES = frozenset({"passed", "failed", "not_run"})
REQUIRED_UNESTABLISHED = (
    "physical S23",
    "sensor-derived Log",
    "ten-bit fidelity",
    "film-stock fidelity",
    "cinema-camera equivalence",
)
MAINTENANCE_NOTE = (
    "physical S23, sensor-derived Log, ten-bit fidelity, film-stock fidelity, "
    "and cinema-camera equivalence are not established"
)

DELETED_FAILED = "deleted-failed-experiment"
PASSES_ONLY = "passes-only-archive"
ONLY_ATTRACTIVE = "only-attractive-renders"
NOTE_INCOMPLETE = "maintenance-limits-not-stated"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
RECORD_KEYS = {"id", "outcome", "retained"}

FAULT_TEXT = {
    DELETED_FAILED: "deleting a failed experiment is rejected",
    PASSES_ONLY: "the archive must include failed and not_run records, not only passes",
    ONLY_ATTRACTIVE: "publishing only attractive renders is rejected",
    NOTE_INCOMPLETE: (
        "maintenance note must state physical S23, sensor-derived Log, ten-bit fidelity, "
        "film-stock fidelity, and cinema-camera equivalence are not established"
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_int(value: object, label: str) -> int:
    require(type(value) is int and not isinstance(value, bool), label + " must be an int")
    return value


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def maintenance_note_complete(note: str) -> bool:
    """True only when every unestablished limit is named and denied."""
    folded = note.casefold()
    if "not established" not in folded:
        return False
    return all(subject.casefold() in folded for subject in REQUIRED_UNESTABLISHED)


def parse_records(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), "records must be a non-empty list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        require(isinstance(item, dict), f"records[{index}] must be an object")
        require(set(item) == RECORD_KEYS, f"records[{index}] keys are invalid")
        outcome = require_text(item["outcome"], f"records[{index}].outcome")
        require(outcome in OUTCOMES, f"records[{index}].outcome is not passed|failed|not_run")
        rows.append({
            "id": require_text(item["id"], f"records[{index}].id"),
            "outcome": outcome,
            "retained": require_bool(item["retained"], f"records[{index}].retained"),
        })
    ids = [row["id"] for row in rows]
    require(len(ids) == len(set(ids)), "record ids must be unique")
    return rows


def _with_mutant(records: list[dict[str, Any]], apply_mutant: bool, only_passes: bool) -> tuple[list[dict[str, Any]], bool]:
    """The mutant deletes failed experiments and publishes only attractive renders."""
    if not apply_mutant:
        return records, only_passes
    mutated = []
    for row in records:
        if row["outcome"] == "failed":
            mutated.append({**row, "retained": False})
        else:
            mutated.append(dict(row))
    return mutated, True


def analyze_archive(
    records: list[dict[str, Any]],
    note: str,
    only_passes: bool,
    apply_mutant: bool,
) -> dict[str, Any]:
    published, published_only_passes = _with_mutant(records, apply_mutant, only_passes)
    deleted = [row["id"] for row in published if row["outcome"] == "failed" and not row["retained"]]
    failed_kept = [row["id"] for row in published if row["outcome"] == "failed" and row["retained"]]
    not_run_kept = [row["id"] for row in published if row["outcome"] == "not_run" and row["retained"]]
    not_run_all = [row["id"] for row in published if row["outcome"] == "not_run"]
    passed = [row["id"] for row in published if row["outcome"] == "passed"]
    note_ok = maintenance_note_complete(note)
    faults: list[str] = []
    if deleted:
        faults.append(DELETED_FAILED)
    if not failed_kept or not not_run_kept:
        faults.append(PASSES_ONLY)
    if published_only_passes:
        faults.append(ONLY_ATTRACTIVE)
    if not note_ok:
        faults.append(NOTE_INCOMPLETE)
    must_keep = {
        "failedExperiments": [row["id"] for row in records if row["outcome"] == "failed"],
        "notRunRecords": [row["id"] for row in records if row["outcome"] == "not_run"],
        "unestablished": list(REQUIRED_UNESTABLISHED),
    }
    snapshot = {
        "passed": passed,
        "failedRetained": failed_kept,
        "failedDeleted": deleted,
        "notRunRetained": not_run_kept,
        "notRun": not_run_all,
        "includesFailed": bool(failed_kept),
        "includesNotRun": bool(not_run_kept),
        "onlyPasses": published_only_passes,
        "maintenanceNoteComplete": note_ok,
        "maintenanceNote": note,
        "applyMutant": apply_mutant,
        "mustKeep": must_keep,
    }
    extra_reasons = [
        "archive rule: " + ARCHIVE_RULE,
        "kept failed " + ", ".join(failed_kept or ["none"]),
        "kept not_run " + ", ".join(not_run_kept or ["none"]),
        "must keep failed experiments, not_run records, and the unestablished limits",
    ]
    if deleted:
        extra_reasons.append("deleted failed experiments: " + ", ".join(deleted))
    if published_only_passes:
        extra_reasons.append("only_passes publishes attractive renders without the unsuccessful record")
        extra_reasons.append("mutant rejected: " + MUTANT)
    elif apply_mutant:
        extra_reasons.append("mutant rejected: " + MUTANT)
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in DECISIONS, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    records = parse_records(mapping["records"])
    note = require_text(mapping["maintenanceNote"], "maintenanceNote")
    only_passes = require_bool(mapping["only_passes"], "only_passes")
    analysis = analyze_archive(records, note, only_passes, apply_mutant)
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["label"] = label
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("evidence archive recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a reproducible archive, or reject a promotional or incomplete one."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document, "document")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
            "oracle: " + ORACLE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core archive payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _core_from_mapping(payload, "payload")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            "fixture: " + FIXTURE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(CASE_COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    repeat = require_text(payload["repeat"], "repeat")
    analysis = _core_from_mapping(payload, "case")
    return {
        "evidence": analysis["evidence"],
        "claim": analysis["claim"],
        "repeat": repeat,
        "faults": list(analysis["faults"]),
        "analysis": analysis,
        "snapshot": analysis["snapshot"],
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    analysis = dict(bundle["analysis"])
    analysis["faults"] = dedupe(list(faults))
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def fixture_records() -> list[dict[str, Any]]:
    """Passes, one retained failure, and one retained not_run record."""
    return [
        {"id": "host-capture", "outcome": "passed", "retained": True},
        {"id": "host-film-render", "outcome": "passed", "retained": True},
        {"id": "host-virtual-lens", "outcome": "passed", "retained": True},
        {"id": "p010-route", "outcome": "failed", "retained": True},
        {"id": "physical-s23", "outcome": "not_run", "retained": True},
    ]


def passes_only_records() -> list[dict[str, Any]]:
    return [row for row in fixture_records() if row["outcome"] == "passed"]


def deleted_failed_records() -> list[dict[str, Any]]:
    rows = fixture_records()
    for row in rows:
        if row["outcome"] == "failed":
            row["retained"] = False
    return rows


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "records": fixture_records(),
        "maintenanceNote": MAINTENANCE_NOTE,
        "only_passes": False,
    }
    payload.update(overrides)
    return payload


def fixture_document() -> dict[str, Any]:
    core = core_payload()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": core["evidenceId"],
        "claim": core["claim"],
        "applyMutant": False,
        "records": core["records"],
        "maintenanceNote": core["maintenanceNote"],
        "only_passes": False,
    }
