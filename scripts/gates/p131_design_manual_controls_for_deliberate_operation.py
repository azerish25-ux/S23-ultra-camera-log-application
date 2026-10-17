#!/usr/bin/env python3
"""P131 Design manual controls for deliberate operation.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A manual control holds a draft string and an applied numeric
value. The applied value changes only on explicit submit of a complete finite
number inside the inclusive advertised range. Partial strings such as "1." and
"" do not change the applied value. Submitting a complete number outside that
range is rejected and leaves the previous applied value. Record and Stop stay
enabled. Setting apply_partial true, which applies every keystroke, is rejected.

Precedence when resolving a proposal: apply_partial, then an unavailable
control, then reset, then an explicit submit. Any rejected proposal keeps the
previous applied value. Draft text stays distinct from the committed target
and from an observed sensor result. The source recording configuration is not
rewritten by the draft.
"""

from __future__ import annotations

import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P131"
WORKSTREAM = 17
TITLE = "Design manual controls for deliberate operation"
GOAL = "Offer precise adjustment without accidental changes during a take."
METHOD = (
    "Provide bounded sliders, numeric entry, reset, and explicit apply behavior where needed. "
    "Keep units visible and disable unavailable controls with reasons. Distinguish draft values "
    "from committed effective targets and observed sensor results."
)
FIXTURE = "A user types an invalid shutter value, rotates the phone, and then returns to the controls."
ORACLE = (
    "The invalid draft is not applied, valid state survives appropriately, and the source "
    "recording configuration remains unchanged."
)
MUTANT = "Apply every partially typed numeric string immediately to the camera."
DELIVERABLE = "Manual interaction contract and draft-state tests"
DEPENDENCIES = ("P130",)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p131-manual-controls"
CLAIM = "manual-control-draft-host-reference"
FIXTURE_CONTROL = "shutter"
FIXTURE_UNIT = "deg"
FIXTURE_DRAFT = "1."
FIXTURE_APPLIED = 180
FIXTURE_MINIMUM = 1
FIXTURE_MAXIMUM = 360
FIXTURE_RESET = 180
FIXTURE_SOURCE = "1080p-sdr"

APPLY_PARTIAL = "apply-partial-keystroke"
PARTIAL_REACHED = "partial-draft-reached-camera"
OUT_OF_RANGE_SUBMIT = "out-of-range-submit"
APPLIED_DIVERGED = "applied-value-diverged"
RECORD_OR_STOP_DISABLED = "record-or-stop-disabled"
SOURCE_CONFIGURATION_CHANGED = "source-configuration-changed"
OBSERVED_REWRITTEN = "draft-rewrote-observed-sensor"
RANGE_CHANGED = "advertised-range-changed"
UNIT_CHANGED = "unit-changed"
CONTROL_IDENTITY_CHANGED = "control-identity-changed"
RESET_VALUE_CHANGED = "reset-value-changed"
UNAVAILABLE_WITHOUT_REASON = "unavailable-without-reason"
UNAVAILABLE_APPLIED = "unavailable-control-applied"
SPURIOUS_REASON = "spurious-unavailable-reason"
RESET_MISSED = "reset-did-not-restore-applied"

DRAFT_RULE = (
    "draft rule: applied changes only on explicit submit of a complete finite number "
    "inside the advertised range"
)

CONTROL_KEYS = (
    "control_id",
    "unit",
    "draft",
    "applied",
    "minimum",
    "maximum",
    "reset_value",
    "submitted",
    "apply_partial",
    "reset",
    "record_enabled",
    "stop_enabled",
    "unavailable",
    "unavailable_reason",
    "source_configuration",
    "observed",
    "orientation",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "committed",
    "proposed",
}
COMMON_KEYS = {"evidenceId", "repeat", "committed", "proposed"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
ORIENTATIONS = frozenset({"landscape", "portrait"})
COMPLETE_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\Z")

FAULT_TEXT = {
    APPLY_PARTIAL: MUTANT,
    PARTIAL_REACHED: "Partially typed input reaching the camera must fail.",
    OUT_OF_RANGE_SUBMIT: "Submitting out of range is rejected and leaves the previous applied value.",
    APPLIED_DIVERGED: "the proposed applied value does not follow the draft rule",
    RECORD_OR_STOP_DISABLED: "Record and Stop stay enabled",
    SOURCE_CONFIGURATION_CHANGED: ORACLE,
    OBSERVED_REWRITTEN: "a draft must not rewrite the observed sensor result",
    RANGE_CHANGED: "the advertised range must not change during the edit",
    UNIT_CHANGED: "units stay visible and unchanged",
    CONTROL_IDENTITY_CHANGED: "a draft edit must not retarget a different control",
    RESET_VALUE_CHANGED: "the advertised reset value must not change during the edit",
    UNAVAILABLE_WITHOUT_REASON: "an unavailable control is disabled with a reason",
    UNAVAILABLE_APPLIED: "an unavailable control must not change the applied value",
    SPURIOUS_REASON: "an available control does not carry an unavailable reason",
    RESET_MISSED: "reset restores the advertised reset value and ignores the draft",
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


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def same_number(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)


def same_optional_number(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return same_number(left, right)


def format_number(value: float) -> str:
    if value == math.trunc(value) and abs(value) < 10**15:
        return str(int(value))
    return format(value, ".12g")


def parse_complete_number(text: str, label: str) -> tuple[float | None, str]:
    """Return (value, kind). Partial strings such as "1." and "" are incomplete."""
    require(isinstance(text, str), label + " must be a string")
    stripped = text.strip()
    if COMPLETE_NUMBER.fullmatch(stripped) is None:
        return None, "incomplete"
    value = float(stripped)
    if not math.isfinite(value):
        return None, "nonfinite"
    return value, "complete"


def parse_control(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(CONTROL_KEYS), label + " keys are invalid")
    control_id = require_text(value["control_id"], label + ".control_id")
    unit = require_text(value["unit"], label + ".unit")
    draft = value["draft"]
    require(isinstance(draft, str), label + ".draft must be a string")
    applied = require_number(value["applied"], label + ".applied")
    minimum = require_number(value["minimum"], label + ".minimum")
    maximum = require_number(value["maximum"], label + ".maximum")
    require(minimum <= maximum, label + " range is inverted")
    reset_value = require_number(value["reset_value"], label + ".reset_value")
    require(minimum <= reset_value <= maximum, label + ".reset_value is outside the advertised range")
    submitted = require_bool(value["submitted"], label + ".submitted")
    apply_partial = require_bool(value["apply_partial"], label + ".apply_partial")
    reset = require_bool(value["reset"], label + ".reset")
    require(not (reset and submitted), label + " cannot both reset and submit")
    record_enabled = require_bool(value["record_enabled"], label + ".record_enabled")
    stop_enabled = require_bool(value["stop_enabled"], label + ".stop_enabled")
    unavailable = require_bool(value["unavailable"], label + ".unavailable")
    reason = value["unavailable_reason"]
    if reason is not None:
        reason = require_text(reason, label + ".unavailable_reason")
    source = require_text(value["source_configuration"], label + ".source_configuration")
    observed = value["observed"]
    if observed is not None:
        observed = require_number(observed, label + ".observed")
    orientation = require_text(value["orientation"], label + ".orientation")
    require(orientation in ORIENTATIONS, label + ".orientation is not recognized")
    if label == "committed":
        require(
            minimum <= applied <= maximum,
            "committed applied is outside the advertised range",
        )
    return {
        "control_id": control_id,
        "unit": unit,
        "draft": draft,
        "applied": applied,
        "minimum": minimum,
        "maximum": maximum,
        "reset_value": reset_value,
        "submitted": submitted,
        "apply_partial": apply_partial,
        "reset": reset,
        "record_enabled": record_enabled,
        "stop_enabled": stop_enabled,
        "unavailable": unavailable,
        "unavailable_reason": reason,
        "source_configuration": source,
        "observed": observed,
        "orientation": orientation,
    }


def in_range(value: float, control: dict[str, Any]) -> bool:
    return control["minimum"] <= value <= control["maximum"]


def legal_outcome(committed: dict[str, Any], proposed: dict[str, Any]) -> tuple[float, str]:
    """Candidate applied value and status. Rejected paths still return the previous value."""
    previous = committed["applied"]
    if proposed["apply_partial"]:
        return previous, "partial-keystroke"
    if proposed["unavailable"]:
        return previous, "unavailable"
    if proposed["reset"]:
        return committed["reset_value"], "reset"
    if not proposed["submitted"]:
        return previous, "held"
    value, kind = parse_complete_number(proposed["draft"], "draft")
    if kind != "complete" or value is None:
        return previous, "partial"
    if not in_range(value, committed):
        return previous, "out-of-range"
    return value, "applied"


def analyze_control(committed: dict[str, Any], proposed: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    previous = committed["applied"]
    value, kind = parse_complete_number(proposed["draft"], "draft")
    candidate, status = legal_outcome(committed, proposed)
    faults: list[str] = []
    if proposed["apply_partial"]:
        faults.append(APPLY_PARTIAL)
    if not (
        committed["record_enabled"]
        and committed["stop_enabled"]
        and proposed["record_enabled"]
        and proposed["stop_enabled"]
    ):
        faults.append(RECORD_OR_STOP_DISABLED)
    if proposed["source_configuration"] != committed["source_configuration"]:
        faults.append(SOURCE_CONFIGURATION_CHANGED)
    if not same_optional_number(committed["observed"], proposed["observed"]):
        faults.append(OBSERVED_REWRITTEN)
    if not same_number(proposed["minimum"], committed["minimum"]) or not same_number(
        proposed["maximum"], committed["maximum"]
    ):
        faults.append(RANGE_CHANGED)
    if proposed["unit"] != committed["unit"]:
        faults.append(UNIT_CHANGED)
    if proposed["control_id"] != committed["control_id"]:
        faults.append(CONTROL_IDENTITY_CHANGED)
    if not same_number(proposed["reset_value"], committed["reset_value"]):
        faults.append(RESET_VALUE_CHANGED)
    if proposed["unavailable"]:
        if proposed["unavailable_reason"] is None:
            faults.append(UNAVAILABLE_WITHOUT_REASON)
    elif proposed["unavailable_reason"] is not None:
        faults.append(SPURIOUS_REASON)
    if status == "out-of-range":
        faults.append(OUT_OF_RANGE_SUBMIT)
    incomplete = kind != "complete"
    reset_explains = status == "reset" and same_number(proposed["applied"], candidate)
    if incomplete and proposed["apply_partial"]:
        faults.append(PARTIAL_REACHED)
    elif incomplete and not same_number(proposed["applied"], previous) and not reset_explains:
        faults.append(PARTIAL_REACHED)
    if not same_number(proposed["applied"], candidate):
        faults.append(APPLIED_DIVERGED)
        if status == "reset":
            faults.append(RESET_MISSED)
        if proposed["unavailable"]:
            faults.append(UNAVAILABLE_APPLIED)
    info = {
        "committed": committed,
        "proposed": proposed,
        "previous": previous,
        "candidate": candidate,
        "status": status,
        "draftKind": kind,
        "draftValue": value,
    }
    return info, faults


def finalize(info: dict[str, Any], faults: list[str]) -> dict[str, Any]:
    ordered = dedupe(faults)
    resolved = dict(info)
    resolved["faults"] = ordered
    resolved["surviving"] = info["candidate"] if not ordered else info["previous"]
    return resolved


def isolation_reasons(info: dict[str, Any]) -> list[str]:
    committed = info["committed"]
    proposed = info["proposed"]
    reasons = [
        DRAFT_RULE,
        "draft="
        + repr(proposed["draft"])
        + " status="
        + info["status"]
        + " applied="
        + format_number(info["surviving"])
        + " previousApplied="
        + format_number(info["previous"]),
        "record_enabled="
        + str(committed["record_enabled"]).lower()
        + " stop_enabled="
        + str(committed["stop_enabled"]).lower(),
        "source_configuration=" + committed["source_configuration"],
        "unit=" + committed["unit"],
    ]
    if info["status"] != "applied":
        reasons.append("uncommitted draft was not applied")
    if proposed["orientation"] != committed["orientation"]:
        reasons.append(
            "orientation " + committed["orientation"] + " -> " + proposed["orientation"]
        )
    if info["status"] == "reset" and not info["faults"]:
        reasons.append("reset restored " + format_number(info["surviving"]))
    observed = "none" if committed["observed"] is None else format_number(committed["observed"])
    reasons.append("observed=" + observed)
    return reasons


def public_control(info: dict[str, Any]) -> dict[str, Any]:
    committed = info["committed"]
    proposed = info["proposed"]
    return {
        "control_id": committed["control_id"],
        "unit": committed["unit"],
        "draft": proposed["draft"],
        "applied": info["surviving"],
        "previousApplied": info["previous"],
        "candidateApplied": info["candidate"],
        "draftKind": info["draftKind"],
        "draftStatus": info["status"],
        "submitted": proposed["submitted"],
        "apply_partial": proposed["apply_partial"],
        "reset": proposed["reset"],
        "record_enabled": committed["record_enabled"],
        "stop_enabled": committed["stop_enabled"],
        "source_configuration": committed["source_configuration"],
        "observed": committed["observed"],
        "orientation": proposed["orientation"],
        "minimum": committed["minimum"],
        "maximum": committed["maximum"],
        "unavailable": proposed["unavailable"],
        "unavailable_reason": proposed["unavailable_reason"],
    }


def make_control(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "control_id": FIXTURE_CONTROL,
        "unit": FIXTURE_UNIT,
        "draft": str(FIXTURE_APPLIED),
        "applied": FIXTURE_APPLIED,
        "minimum": FIXTURE_MINIMUM,
        "maximum": FIXTURE_MAXIMUM,
        "reset_value": FIXTURE_RESET,
        "submitted": False,
        "apply_partial": False,
        "reset": False,
        "record_enabled": True,
        "stop_enabled": True,
        "unavailable": False,
        "unavailable_reason": None,
        "source_configuration": FIXTURE_SOURCE,
        "observed": None,
        "orientation": "portrait",
    }
    value.update(overrides)
    return value


def held_proposal(**overrides: Any) -> dict[str, Any]:
    value = make_control(draft=FIXTURE_DRAFT, submitted=False, orientation="landscape")
    value.update(overrides)
    return value


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "committed": make_control(),
        "proposed": held_proposal(),
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": dedupe(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return result


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    committed = parse_control(payload["committed"], "committed")
    proposed = parse_control(payload["proposed"], "proposed")
    info, faults = analyze_control(committed, proposed)
    info = finalize(info, faults)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "committed": committed,
        "proposed": proposed,
        "info": info,
        "faults": list(info["faults"]),
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(isolation_reasons(bundle["info"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if not ordered:
        reasons.append("manual control recorded; draft stayed distinct from the applied target")
    preserved = [bundle["evidence"], public_control(bundle["info"]), *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def assess(document: dict) -> dict[str, Any]:
    """Record a deliberate manual edit, or reject a draft that moves the applied value."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(
        type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
        "schemaVersion must be 1",
    )
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    committed = parse_control(document["committed"], "committed")
    proposed = parse_control(document["proposed"], "proposed")
    info, faults = analyze_control(committed, proposed)
    if apply_mutant:
        faults.append(APPLY_PARTIAL)
    info = finalize(info, faults)
    ordered = list(info["faults"])
    reasons = [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    reasons.extend(isolation_reasons(info))
    for token in ordered:
        reasons.append(FAULT_TEXT[token])
    if APPLY_PARTIAL in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append(
            "manual control recorded; draft stayed distinct from the applied target; "
            "not a physical qualification"
        )
    preserved = [evidence, public_control(info), claim]
    return assemble(PHASE, ordered, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)
