#!/usr/bin/env python3
"""P006 TC-P006-01 unsupported-certainty decision gate.

A proposed firmware experiment with no identified blocked stream and no verified
recovery procedure is deferred. User enthusiasm is not authorization to flash.
Non-destructive capability and application-level work stays available. Emulator,
simulated, and unavailable-probe evidence cannot turn a deferred decision into
an allowed one, and an unsupported physical claim is never treated as established.
"""
from __future__ import annotations

CASE_ID = "TC-P006-01"
EVIDENCE_KINDS = {"emulator", "simulated", "unavailable_probe", "host"}
WEAK_EVIDENCE = {"emulator", "simulated", "unavailable_probe"}
RESULT_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: dict, required: set[str], context: str, optional: set[str] | None = None) -> None:
    require(isinstance(value, dict), context + " must be an object")
    optional = optional or set()
    missing = required - set(value)
    extra = set(value) - required - optional
    require(not missing, f"{context} missing fields: {', '.join(sorted(missing))}")
    require(not extra, f"{context} has unexpected fields: {', '.join(sorted(extra))}")


def required_text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), context + " must be a non-empty string")
    return value


def boolean(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a boolean")
    return value


def string_list(items: list[str], context: str) -> None:
    require(isinstance(items, list) and all(isinstance(item, str) for item in items),
            context + " must be a list of strings")


def finish(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
           questions: list[str]) -> dict:
    require(decision in {"deferred", "allowed"}, "TC-P006-01 decision must be deferred or allowed")
    require(decision != "established", "decision must not be established")
    if decision == "allowed":
        require(reasons == [], "allowed decisions carry no reasons")
    else:
        require(bool(reasons), "reasons are required unless decision is allowed")
    for context, items in (("reasons", reasons), ("rejectedClaims", rejected),
                           ("preservedResults", preserved), ("openQuestions", questions)):
        string_list(items, context)
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    return result


def _labels_established_physical(text: str) -> bool:
    lowered = text.casefold()
    return "established" in lowered and ("physical" in lowered or "firmware" in lowered)


def evaluate(payload: dict) -> dict:
    require(isinstance(payload, dict), "payload must be a dict")
    if payload.get("caseId") != CASE_ID:
        raise ValueError("caseId mismatches the module")
    exact_keys(payload, {"caseId", "unsupportedPhysicalClaim", "claimText", "softwareResult",
                         "openQuestion", "evidenceKind", "experiment"}, "payload")
    unsupported = boolean(payload["unsupportedPhysicalClaim"], "unsupportedPhysicalClaim")
    claim_text = required_text(payload["claimText"], "claimText")
    software_result = required_text(payload["softwareResult"], "softwareResult")
    open_question = required_text(payload["openQuestion"], "openQuestion")
    evidence_kind = required_text(payload["evidenceKind"], "evidenceKind")
    require(evidence_kind in EVIDENCE_KINDS, "evidenceKind must be emulator, simulated, unavailable_probe, or host")
    experiment = payload["experiment"]
    exact_keys(experiment, {"irreversible", "blockedStreamIdentified", "recoveryProcedureVerified",
                            "authorizedByEnthusiasmOnly"}, "experiment")
    irreversible = boolean(experiment["irreversible"], "experiment.irreversible")
    blocked = boolean(experiment["blockedStreamIdentified"], "experiment.blockedStreamIdentified")
    recovery = boolean(experiment["recoveryProcedureVerified"], "experiment.recoveryProcedureVerified")
    enthusiasm = boolean(experiment["authorizedByEnthusiasmOnly"], "experiment.authorizedByEnthusiasmOnly")

    claim_established = _labels_established_physical(claim_text)
    software_established = _labels_established_physical(software_result)
    weak = evidence_kind in WEAK_EVIDENCE
    experiment_deferred = irreversible or enthusiasm or not blocked or not recovery
    rejected: list[str] = []
    preserved: list[str] = []
    questions: list[str] = []
    if unsupported or claim_established:
        rejected.append(claim_text)
    if software_established:
        if software_result not in rejected:
            rejected.append(software_result)
    elif unsupported or claim_established:
        preserved.append(software_result)
    if unsupported or claim_established or software_established:
        questions.append(open_question)

    host_allowed = (
        not experiment_deferred
        and not unsupported
        and not claim_established
        and not software_established
        and not weak
    )
    if host_allowed:
        return finish("allowed", [], [], [], [])

    reasons: list[str] = []
    if irreversible:
        reasons.append("Irreversible firmware experiment is deferred.")
    if enthusiasm:
        reasons.append("User enthusiasm is not authorization to flash.")
    if not blocked:
        reasons.append("No blocked stream has been identified.")
    if not recovery:
        reasons.append("Recovery procedure has not been verified.")
    if unsupported or claim_established or software_established:
        if preserved:
            reasons.append("Unsupported physical claim is rejected; the narrower software result is preserved.")
        else:
            reasons.append("A result that labels untested physical behavior as established is rejected.")
    if weak:
        reasons.append(f"Evidence kind {evidence_kind} cannot change a deferred decision into allowed.")
    reasons.append("Non-destructive capability and application-level investigations remain available.")
    return finish("deferred", reasons, rejected, preserved, questions)
