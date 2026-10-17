#!/usr/bin/env python3
"""P134 Design transparent progress and failure states.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Progress is either indeterminate or accounted_frames/expected_frames.
It cannot be 1.0 until drain_complete is true and every frame is accounted.
Showing 100 percent when drain_complete is false is rejected. A failure must
include a non-empty reason and success false. A success banner with a failure
reason is rejected. When expected_frames is 0 the state is indeterminate; no
percentage is invented. Completion still waits for verification and publication.
"""

from __future__ import annotations

import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P134"
WORKSTREAM = 17
TITLE = "Design transparent progress and failure states"
GOAL = "Tell users what is happening without fabricated percentages or vague success banners."
METHOD = (
    "Progress should identify capture, inference, rendering, verification, or publication. "
    "Use indeterminate states when remaining work is unknown. Errors distinguish unsupported "
    "mode, unavailable model, source corruption, output failure, and retained recoverable footage."
)
FIXTURE = (
    "A render reaches its final frame but still requires full decode verification and "
    "gallery publication."
)
ORACLE = "The UI does not show completed until acceptance and publication policy are satisfied."
MUTANT = "Show one hundred percent success immediately after the last frame is submitted to the encoder."
DELIVERABLE = "Progress semantics and failure-state screenshots/tests"
DEPENDENCIES = ("P133",)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p134-progress-failure"
CLAIM = "transparent-progress-and-failure-host-reference"
RULE = (
    "progress is either indeterminate or accounted_frames/expected_frames; "
    "it cannot be 1.0 until drain_complete is true and every frame is accounted"
)

STAGES = frozenset({"capture", "inference", "rendering", "verification", "publication"})
FAILURE_KINDS = frozenset({
    "unsupported-mode",
    "unavailable-model",
    "source-corruption",
    "output-failure",
    "retained-recoverable-footage",
})
RETAINED_KIND = "retained-recoverable-footage"

HUNDRED_BEFORE_DRAIN = "hundred-percent-while-drain-incomplete"
INVENTED_ZERO = "invented-percentage-when-expected-frames-is-zero"
INVENTED_BEFORE_DRAIN = "invented-percentage-while-ratio-withheld"
FABRICATED_PERCENT = "fabricated-progress-percentage"
SUCCESS_WITH_REASON = "success-banner-with-failure-reason"
PREMATURE_COMPLETE = "completed-before-acceptance-and-publication"
MUTANT_TOKEN = "hundred-percent-success-after-encoder-submit"
ORPHAN_REASON = "failure-reason-without-failure"
FOOTAGE_DROPPED = "recoverable-footage-not-retained"
PUBLICATION_BEFORE_VERIFICATION = "publication-before-verification"
VERIFICATION_BEFORE_DRAIN = "verification-before-drain-and-accounted-frames"

FAILURE_REQUIRES_REASON = "a failure must include a non-empty reason and success false"

PROGRESS_KEYS = (
    "stage",
    "accounted_frames",
    "expected_frames",
    "drain_complete",
    "displayed_percent",
    "success",
    "failure_reason",
    "failure_kind",
    "verification_complete",
    "publication_complete",
    "footage_retained",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "progress",
}
COMMON_KEYS = {"evidenceId", "repeat", "progress"}
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
COMPLETE_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\Z")

FAULT_TEXT = {
    HUNDRED_BEFORE_DRAIN: "showing 100 percent when drain_complete is false is rejected",
    INVENTED_ZERO: "do not invent a percentage when expected_frames is 0; that state is indeterminate",
    INVENTED_BEFORE_DRAIN: (
        "do not invent a percentage when accounted_frames/expected_frames would be 1.0 before drain_complete"
    ),
    FABRICATED_PERCENT: "displayed percent must equal accounted_frames/expected_frames when that ratio is known",
    SUCCESS_WITH_REASON: "a success banner with a failure reason is rejected",
    PREMATURE_COMPLETE: ORACLE,
    MUTANT_TOKEN: MUTANT,
    ORPHAN_REASON: FAILURE_REQUIRES_REASON,
    FOOTAGE_DROPPED: "retained recoverable footage must stay retained",
    PUBLICATION_BEFORE_VERIFICATION: "publication cannot complete before full decode verification",
    VERIFICATION_BEFORE_DRAIN: (
        "verification cannot complete before drain_complete and every frame is accounted"
    ),
}

PHASE_CASE = {
    "id": PHASE,
    "expected": ORACLE,
    "repeat": "Repeat encoder drain, full decode, sidecar export, and gallery commit.",
    "negative": MUTANT,
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


def require_count(value: object, label: str) -> int:
    require(type(value) is int, label + " must be an int")
    require(value >= 0, label + " must be >= 0")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def require_optional_bool(value: object, label: str) -> bool | None:
    if value is None:
        return None
    return require_bool(value, label)


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def is_hundred(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    number = float(value)
    if not math.isfinite(number):
        return False
    return math.isclose(number, 100.0, rel_tol=0.0, abs_tol=1e-9)


def progress_reading(accounted_frames: object, expected_frames: object, drain_complete: object) -> dict[str, Any]:
    """Return the only legal progress reading.

    expected_frames == 0 is indeterminate and has no fraction.
    Otherwise the fraction is accounted_frames/expected_frames, except that a
    ratio of 1.0 is withheld until drain_complete is true and every frame is
    accounted. The withheld reading is indeterminate so a percentage is not invented.
    """
    accounted = require_count(accounted_frames, "accounted_frames")
    expected = require_count(expected_frames, "expected_frames")
    drain = require_bool(drain_complete, "drain_complete")
    require(accounted <= expected, "accounted_frames cannot exceed expected_frames")
    if expected == 0:
        return {
            "state": "indeterminate",
            "fraction": None,
            "every_frame_accounted": False,
            "drain_complete": drain,
            "allows_one": False,
        }
    every = accounted == expected
    if every and drain:
        fraction: float | None = 1.0
        state = "fraction"
        allows = True
    elif every and not drain:
        fraction = None
        state = "indeterminate"
        allows = False
    else:
        fraction = accounted / expected
        state = "fraction"
        allows = False
        require(fraction is not None and fraction < 1.0, "fraction cannot be 1.0 before drain and full accounting")
    if fraction == 1.0:
        require(allows and drain and every, "fraction cannot be 1.0 until drain_complete and every frame is accounted")
    return {
        "state": state,
        "fraction": fraction,
        "every_frame_accounted": every,
        "drain_complete": drain,
        "allows_one": allows,
    }


def spoken_progress(reading: dict[str, Any]) -> str:
    if reading["state"] == "indeterminate" or reading["fraction"] is None:
        return "indeterminate"
    return format(reading["fraction"], ".12g")


def parse_progress(value: Any, label: str = "progress") -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(PROGRESS_KEYS), label + " keys are invalid")
    stage = require_text(value["stage"], label + ".stage")
    require(stage in STAGES, label + ".stage is not recognized")
    accounted = require_count(value["accounted_frames"], label + ".accounted_frames")
    expected = require_count(value["expected_frames"], label + ".expected_frames")
    drain = require_bool(value["drain_complete"], label + ".drain_complete")
    displayed = value["displayed_percent"]
    if displayed is not None:
        displayed = require_number(displayed, label + ".displayed_percent")
        require(0.0 <= displayed <= 100.0, label + ".displayed_percent must be from 0 through 100")
    success = require_optional_bool(value["success"], label + ".success")
    reason = value["failure_reason"]
    kind = value["failure_kind"]
    if success is False:
        require(
            isinstance(reason, str) and bool(reason.strip()) and reason == reason.strip(),
            FAILURE_REQUIRES_REASON,
        )
        require(isinstance(kind, str) and kind in FAILURE_KINDS, FAILURE_REQUIRES_REASON)
    else:
        if reason is not None:
            reason = require_text(reason, label + ".failure_reason")
        if kind is not None:
            kind = require_text(kind, label + ".failure_kind")
            require(kind in FAILURE_KINDS, label + ".failure_kind is not recognized")
    verification = require_bool(value["verification_complete"], label + ".verification_complete")
    publication = require_bool(value["publication_complete"], label + ".publication_complete")
    retained = require_bool(value["footage_retained"], label + ".footage_retained")
    return {
        "stage": stage,
        "accounted_frames": accounted,
        "expected_frames": expected,
        "drain_complete": drain,
        "displayed_percent": displayed,
        "success": success,
        "failure_reason": reason,
        "failure_kind": kind,
        "verification_complete": verification,
        "publication_complete": publication,
        "footage_retained": retained,
    }


def analyze_progress(progress: dict[str, Any]) -> dict[str, Any]:
    reading = progress_reading(
        progress["accounted_frames"],
        progress["expected_frames"],
        progress["drain_complete"],
    )
    faults: list[str] = []
    displayed = progress["displayed_percent"]
    if reading["state"] == "indeterminate":
        if displayed is not None:
            if progress["expected_frames"] == 0:
                faults.append(INVENTED_ZERO)
            else:
                faults.append(INVENTED_BEFORE_DRAIN)
            if is_hundred(displayed) and not progress["drain_complete"]:
                faults.append(HUNDRED_BEFORE_DRAIN)
    else:
        expected_percent = float(reading["fraction"]) * 100.0
        if displayed is not None and not math.isclose(
            displayed, expected_percent, rel_tol=1e-9, abs_tol=1e-9
        ):
            faults.append(FABRICATED_PERCENT)
        if displayed is not None and is_hundred(displayed) and not reading["allows_one"]:
            if not progress["drain_complete"]:
                faults.append(HUNDRED_BEFORE_DRAIN)
            else:
                faults.append(FABRICATED_PERCENT)
    if reading["fraction"] == 1.0 and not reading["allows_one"]:
        faults.append(HUNDRED_BEFORE_DRAIN)
    reason = progress["failure_reason"]
    kind = progress["failure_kind"]
    success = progress["success"]
    if success is True and (reason is not None or kind is not None):
        faults.append(SUCCESS_WITH_REASON)
    acceptance = (
        reading["allows_one"]
        and progress["verification_complete"]
        and progress["publication_complete"]
    )
    if success is True and not acceptance:
        faults.append(PREMATURE_COMPLETE)
    if success is True and is_hundred(displayed) and not progress["drain_complete"]:
        faults.append(MUTANT_TOKEN)
    if success is None and (reason is not None or kind is not None):
        faults.append(ORPHAN_REASON)
    if kind == RETAINED_KIND and not progress["footage_retained"]:
        faults.append(FOOTAGE_DROPPED)
    if progress["publication_complete"] and not progress["verification_complete"]:
        faults.append(PUBLICATION_BEFORE_VERIFICATION)
    if progress["verification_complete"] and not reading["allows_one"]:
        faults.append(VERIFICATION_BEFORE_DRAIN)
    info = dict(reading)
    info["acceptance"] = acceptance
    info["faults"] = dedupe(faults)
    info["progress"] = progress
    return info


def reading_line(info: dict[str, Any]) -> str:
    if info["fraction"] is None:
        shown = "none"
    else:
        shown = format(info["fraction"], ".12g")
    return (
        "progress state="
        + info["state"]
        + " fraction="
        + shown
        + " drain_complete="
        + ("true" if info["drain_complete"] else "false")
        + " every_frame_accounted="
        + ("true" if info["every_frame_accounted"] else "false")
        + " allows_one="
        + ("true" if info["allows_one"] else "false")
    )


def public_progress(info: dict[str, Any]) -> dict[str, Any]:
    progress = info["progress"]
    fraction = info["fraction"]
    if fraction == 1.0:
        require(info["allows_one"] and info["drain_complete"], "refusing to publish fraction 1.0")
    return {
        "stage": progress["stage"],
        "state": info["state"],
        "fraction": fraction,
        "accounted_frames": progress["accounted_frames"],
        "expected_frames": progress["expected_frames"],
        "drain_complete": progress["drain_complete"],
        "every_frame_accounted": info["every_frame_accounted"],
        "allows_one": info["allows_one"],
        "displayed_percent": progress["displayed_percent"],
        "success": progress["success"],
        "failure_reason": progress["failure_reason"],
        "failure_kind": progress["failure_kind"],
        "verification_complete": progress["verification_complete"],
        "publication_complete": progress["publication_complete"],
        "footage_retained": progress["footage_retained"],
        "acceptance_satisfied": info["acceptance"],
    }


def fixture_progress(**overrides: Any) -> dict[str, Any]:
    progress: dict[str, Any] = {
        "stage": "verification",
        "accounted_frames": 12,
        "expected_frames": 12,
        "drain_complete": False,
        "displayed_percent": None,
        "success": None,
        "failure_reason": None,
        "failure_kind": None,
        "verification_complete": False,
        "publication_complete": False,
        "footage_retained": True,
    }
    progress.update(overrides)
    return progress


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "progress": fixture_progress(),
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
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def progress_reasons(info: dict[str, Any]) -> list[str]:
    progress = info["progress"]
    reasons = [
        RULE,
        reading_line(info),
        "stage=" + progress["stage"],
    ]
    if info["every_frame_accounted"] and not info["drain_complete"] and progress["expected_frames"] > 0:
        reasons.append(
            "ratio withheld: accounted_frames/expected_frames would be 1.0 before drain_complete"
        )
    if progress["expected_frames"] == 0:
        reasons.append("expected_frames is 0; progress is indeterminate")
    if progress["success"] is False:
        reasons.append("failure success=false reason=" + str(progress["failure_reason"]))
    if info["acceptance"]:
        reasons.append("acceptance and publication policy satisfied")
    else:
        reasons.append("acceptance and publication policy are not satisfied")
    return reasons


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    progress = parse_progress(payload["progress"], "progress")
    info = analyze_progress(progress)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "progress": progress,
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
    reasons.extend(progress_reasons(bundle["info"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if MUTANT_TOKEN in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("progress recorded without a fabricated percentage or a false success banner")
    preserved = [bundle["evidence"], public_progress(bundle["info"]), *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def assess(document: dict) -> dict[str, Any]:
    """Record an honest progress or failure reading, or reject a fabricated completion."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    progress = parse_progress(document["progress"], "progress")
    info = analyze_progress(progress)
    faults = list(info["faults"])
    if apply_mutant and MUTANT_TOKEN not in faults:
        faults.append(MUTANT_TOKEN)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    reasons.extend(progress_reasons(info))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(FAULT_TEXT[token])
    if MUTANT_TOKEN in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("progress recorded without a fabricated percentage or a false success banner")
    preserved = [evidence, public_progress(info), claim]
    return assemble(PHASE, ordered, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def evaluate(payload: dict) -> dict:
    """Evaluate one progress payload. Same result contract as assess."""
    bundle = begin_case(payload, set())
    return finish_case(PHASE_CASE, bundle, bundle["faults"], [])


def parse_complete_number(text: str, label: str) -> tuple[float | None, str]:
    require(isinstance(text, str), label + " must be a string")
    stripped = text.strip()
    if COMPLETE_NUMBER.fullmatch(stripped) is None:
        return None, "incomplete"
    value = float(stripped)
    if not math.isfinite(value):
        return None, "invalid"
    return value, "complete"
