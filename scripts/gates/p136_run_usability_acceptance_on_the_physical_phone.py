#!/usr/bin/env python3
"""P136 Run usability acceptance on the physical phone.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P136-01 through TC-P136-08 modules.

A usability report needs session_count, device_id, measured_on_device, and
findings. Approving the UI (approved true) from a desktop screenshot
(measured_on_device false) is rejected. An honest report with
measured_on_device false and approved false is recorded as not run. Findings
that claim a physical pass without a device measurement id are rejected.
This module does not invent a shooting workflow result. Decision is only
recorded or rejected, never qualified or allowed.
"""

from __future__ import annotations

import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P136"
WORKSTREAM = 17
TITLE = "Run usability acceptance on the physical phone"
SLUG = "run_usability_acceptance_on_the_physical_phone"
GOAL = "Validate real shooting ergonomics rather than relying on static mockups."
METHOD = (
    "Test outdoor readability, one-handed operation, landscape framing, gloves where relevant, "
    "large text, interruptions, and recovery discovery. Observe user tasks and errors. "
    "Keep aesthetic preferences separate from measurable task completion and footage safety."
)
FIXTURE = (
    "A user starts a take, receives a thermal warning, stops, finds the retained clip, "
    "and shares its evidence."
)
ORACLE = "The task completes without hidden controls or ambiguity about whether footage was saved."
MUTANT = "Approve the UI from a desktop screenshot without a real shooting workflow."
DELIVERABLE = "Physical usability report and prioritized corrections"
DEPENDENCIES = ("P135",)
OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p136-usability"
CLAIM = "physical-usability-not-run"
SCHEMA_VERSION = 1

DESKTOP_SCREENSHOT_APPROVAL = "desktop-screenshot-approval"
APPROVAL_WITHOUT_WORKFLOW = "approval-without-observed-shooting-workflow"
PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID = "physical-pass-without-measurement-id"
AESTHETIC_AS_TASK = "aesthetic-preference-as-task-completion"
SHOOTING_WORKFLOW_NOT_OBSERVED = "shooting-workflow-not-observed"

FAULT_ORDER = (
    DESKTOP_SCREENSHOT_APPROVAL,
    APPROVAL_WITHOUT_WORKFLOW,
    PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID,
    AESTHETIC_AS_TASK,
    SHOOTING_WORKFLOW_NOT_OBSERVED,
)
FAULT_TEXT = {
    DESKTOP_SCREENSHOT_APPROVAL: MUTANT,
    APPROVAL_WITHOUT_WORKFLOW: (
        "approval without an observed shooting workflow is rejected"
    ),
    PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID: (
        "findings that claim a physical pass without a device measurement id are rejected"
    ),
    AESTHETIC_AS_TASK: (
        "aesthetic preferences must stay separate from measurable task completion and footage safety"
    ),
    SHOOTING_WORKFLOW_NOT_OBSERVED: "shooting workflow result was not invented",
}
CORRECTION_TEXT = {
    DESKTOP_SCREENSHOT_APPROVAL: (
        "Do not approve the UI from a desktop screenshot; observe the physical shooting workflow."
    ),
    APPROVAL_WITHOUT_WORKFLOW: (
        "Do not approve usability until a physical shooting workflow is observed."
    ),
    PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID: (
        "Do not record a physical pass without a device measurement id."
    ),
    AESTHETIC_AS_TASK: (
        "Keep aesthetic preference separate from task completion and footage safety."
    ),
    SHOOTING_WORKFLOW_NOT_OBSERVED: (
        "Do not invent a shooting workflow result from an unobserved session."
    ),
}

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "session_count",
    "device_id",
    "measured_on_device",
    "approved",
    "findings",
}
REPORT_KEYS = {
    "session_count",
    "device_id",
    "measured_on_device",
    "approved",
    "findings",
}
FINDING_KEYS = {
    "finding_id",
    "claims_physical_pass",
    "measurement_id",
    "aesthetic_only",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"recorded", "rejected"}
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "fixed cadence was not established",
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
COMPLETE_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
NOT_RUN_REASON = "usability acceptance recorded as not run"


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


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def require_count(value: object, label: str) -> int:
    require(type(value) is int, label + " must be an int")
    require(value >= 0, label + " must be >= 0")
    return value


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def parse_draft_number(text: str) -> tuple[float | None, str]:
    """Classify a control draft as complete, incomplete, or invalid."""
    require(isinstance(text, str), "draft must be a string")
    if COMPLETE_NUMBER.fullmatch(text) is None:
        return None, "incomplete"
    value = float(text)
    if not math.isfinite(value):
        return None, "invalid"
    return value, "complete"


def _device_id(value: object, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label)


def _measurement_id(value: object, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label)


def parse_findings(value: object, label: str) -> list[dict[str, Any]]:
    require(type(value) is list, label + " must be a list")
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        prefix = f"{label}[{index}]"
        require(isinstance(item, dict), prefix + " must be an object")
        require(set(item) == FINDING_KEYS, prefix + " keys are invalid")
        finding_id = require_text(item["finding_id"], prefix + ".finding_id")
        require(finding_id not in seen, prefix + ".finding_id is duplicated")
        seen.add(finding_id)
        parsed.append(
            {
                "finding_id": finding_id,
                "claims_physical_pass": require_bool(
                    item["claims_physical_pass"], prefix + ".claims_physical_pass"
                ),
                "measurement_id": _measurement_id(
                    item["measurement_id"], prefix + ".measurement_id"
                ),
                "aesthetic_only": require_bool(item["aesthetic_only"], prefix + ".aesthetic_only"),
            }
        )
    return parsed


def parse_usability(source: dict, label: str) -> dict[str, Any]:
    """Read the usability report fields. Does not invent a workflow outcome."""
    require(isinstance(source, dict), label + " must be an object")
    return {
        "session_count": require_count(source["session_count"], label + ".session_count"),
        "device_id": _device_id(source["device_id"], label + ".device_id"),
        "measured_on_device": require_bool(
            source["measured_on_device"], label + ".measured_on_device"
        ),
        "approved": require_bool(source["approved"], label + ".approved"),
        "findings": parse_findings(source["findings"], label + ".findings"),
    }


def parse_report(value: object) -> dict[str, Any]:
    require(isinstance(value, dict), "report must be an object")
    require(set(value) == REPORT_KEYS, "report keys are invalid")
    return parse_usability(value, "report")


def physical_sessions(report: dict[str, Any]) -> int:
    """Desktop sessions do not count as physical S23 sessions."""
    if report["measured_on_device"] is not True:
        return 0
    return report["session_count"]


def has_device_measurement_id(report: dict[str, Any], finding: dict[str, Any]) -> bool:
    """A device measurement id needs a measured session, a device, and an id."""
    if finding["measurement_id"] is None:
        return False
    if report["device_id"] is None:
        return False
    if report["measured_on_device"] is not True:
        return False
    if physical_sessions(report) < 1:
        return False
    return True


def usability_faults(report: dict[str, Any]) -> list[str]:
    faults: list[str] = []
    measured = report["measured_on_device"]
    approved = report["approved"]
    if approved and not measured:
        faults.append(DESKTOP_SCREENSHOT_APPROVAL)
    if approved and measured:
        faults.append(APPROVAL_WITHOUT_WORKFLOW)
    claims_pass = [item for item in report["findings"] if item["claims_physical_pass"]]
    if any(not has_device_measurement_id(report, item) for item in claims_pass):
        faults.append(PHYSICAL_PASS_WITHOUT_MEASUREMENT_ID)
    if any(item["aesthetic_only"] and item["claims_physical_pass"] for item in report["findings"]):
        faults.append(AESTHETIC_AS_TASK)
    if measured:
        faults.append(SHOOTING_WORKFLOW_NOT_OBSERVED)
    return [token for token in FAULT_ORDER if token in faults]


def corrections_for(faults: list[str], extra: dict[str, str] | None = None) -> list[str]:
    text = dict(CORRECTION_TEXT)
    if extra:
        text.update(extra)
    return [text[token] for token in faults if token in text]


def public_report(report: dict[str, Any], faults: list[str]) -> dict[str, Any]:
    status = "rejected" if faults else "not-run"
    return {
        "session_count": report["session_count"],
        "device_id": report["device_id"],
        "measured_on_device": report["measured_on_device"],
        "approved": report["approved"],
        "physical_sessions": physical_sessions(report),
        "findings": [dict(item) for item in report["findings"]],
        "status": status,
        "shootingWorkflow": None,
        "corrections": corrections_for(faults),
    }


def report_reason_lines(report: dict[str, Any]) -> list[str]:
    device = report["device_id"] if report["device_id"] is not None else "none"
    lines = [
        (
            f"session_count={report['session_count']} "
            f"physical_sessions={physical_sessions(report)} "
            f"device_id={device} "
            f"measured_on_device={str(report['measured_on_device']).lower()} "
            f"approved={str(report['approved']).lower()} "
            f"findings={len(report['findings'])}"
        ),
        "shooting workflow result was not invented",
    ]
    if report["measured_on_device"] is not True:
        lines.append("measured_on_device false is a desktop screenshot, not a physical S23 session")
    if physical_sessions(report) == 0:
        lines.append("physical_sessions is 0; desktop session_count is not a device measurement")
    return lines


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in DECISIONS, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(reasons and all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    require(all(isinstance(item, str) and item for item in faults), "rejectedClaims must be strings")
    require(evidence in preserved, "evidence must be preserved")
    require(open_questions and open_questions[0] == OPEN_QUESTION, "openQuestions must say physical S23 measurement was not run")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(faults),
        "preservedResults": list(preserved),
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    return result


def honest_report(**overrides: Any) -> dict[str, Any]:
    report = {
        "session_count": 0,
        "device_id": None,
        "measured_on_device": False,
        "approved": False,
        "findings": [],
    }
    report.update(overrides)
    return report


def fixture_document() -> dict[str, Any]:
    report = honest_report()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "session_count": report["session_count"],
        "device_id": report["device_id"],
        "measured_on_device": report["measured_on_device"],
        "approved": report["approved"],
        "findings": report["findings"],
    }


def _reason_block(report: dict[str, Any], faults: list[str], headline: list[str]) -> list[str]:
    reasons = list(headline)
    reasons.extend(report_reason_lines(report))
    for token in faults:
        reasons.append(FAULT_TEXT[token])
    if DESKTOP_SCREENSHOT_APPROVAL in faults:
        reasons.append("mutant rejected: " + MUTANT)
    if not faults:
        reasons.append(NOT_RUN_REASON)
        reasons.append("no prioritized physical corrections; usability acceptance was not run")
        reasons.append("deliverable recorded as not run: " + DELIVERABLE)
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record an honest not-run usability report, or reject a screenshot approval."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == SCHEMA_VERSION, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    report = parse_usability(document, "document")
    faults = usability_faults(report)
    reasons = _reason_block(
        report,
        faults,
        [
            "host reference only; not a physical S23 measurement",
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
            "oracle: " + ORACLE,
        ],
    )
    preserved = [evidence, public_report(report, faults), claim]
    return assemble(PHASE, faults, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def evaluate(document: dict) -> dict[str, Any]:
    """Same contract as assess."""
    return assess(document)


def finish_tc(
    case: dict,
    evidence: str,
    repeat: str,
    report: dict[str, Any],
    case_faults: list[str],
    case_reasons: list[str],
    case_preserved: list,
    fault_text: dict[str, str],
    correction_text: dict[str, str] | None = None,
) -> dict[str, Any]:
    report_fault_list = usability_faults(report)
    ordered = dedupe(list(report_fault_list) + list(case_faults))
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + repeat,
    ]
    reasons.extend(report_reason_lines(report))
    reasons.extend(case_reasons)
    text = dict(FAULT_TEXT)
    text.update(fault_text)
    for token in ordered:
        reasons.append(text.get(token, token))
    if DESKTOP_SCREENSHOT_APPROVAL in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append(NOT_RUN_REASON)
        reasons.append("host check recorded; not a physical qualification")
    preserved_report = public_report(report, ordered)
    if correction_text:
        preserved_report["corrections"] = corrections_for(ordered, correction_text)
    preserved = [evidence, preserved_report, *case_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, evidence)
