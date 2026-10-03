#!/usr/bin/env python3
"""P008 TC-P008-01 unsupported-certainty decision gate.

A phase whose host gate passed while the physical device gate is still pending
is software-verified only. A concurrent remote commit is preserved. Completion
is not invented from a local build, from marking every phase complete, or from
emulator, simulated, or unavailable-probe evidence. An unsupported physical
claim is rejected and is never reported as established or complete.
"""
from __future__ import annotations

CASE_ID = "TC-P008-01"
EVIDENCE_KINDS = {"emulator", "simulated", "unavailable_probe", "host"}
WEAK_EVIDENCE = {"emulator", "simulated", "unavailable_probe"}
HOST_GATES = {"passed", "failed"}
PHYSICAL_GATES = {"pending", "passed", "failed"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
PENDING_QUESTION = "physical device gate pending"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def required_text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), context + " must be a non-empty string")
    return value


def boolean(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a boolean")
    return value


def string_list(items: list[str], context: str) -> None:
    require(
        isinstance(items, list) and all(isinstance(item, str) for item in items),
        context + " must be a list of strings",
    )


def finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    require(
        decision in {"software_verified_only", "blocked", "complete"},
        "unexpected TC-P008-01 decision",
    )
    require(decision != "established", "decision must not be established")
    require(decision != "allowed", "TC-P008-01 does not return allowed")
    require(bool(reasons), "reasons are required unless decision is allowed")
    for context, items in (
        ("reasons", reasons),
        ("rejectedClaims", rejected),
        ("preservedResults", preserved),
        ("openQuestions", questions),
    ):
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


def evaluate(payload: dict) -> dict:
    require(isinstance(payload, dict), "payload must be a dict")
    require(payload.get("caseId") == CASE_ID, "caseId mismatches the module")
    required = {
        "caseId",
        "hostGate",
        "physicalGate",
        "localBuildSucceeded",
        "markAllPhasesComplete",
        "unsupportedPhysicalClaim",
        "claimText",
        "softwareResult",
        "openQuestion",
        "evidenceKind",
        "remoteCommit",
    }
    missing = required - set(payload)
    require(not missing, "bad payload: missing " + ", ".join(sorted(missing)))

    host = required_text(payload["hostGate"], "hostGate")
    require(host in HOST_GATES, "hostGate must be passed or failed")
    physical = required_text(payload["physicalGate"], "physicalGate")
    require(physical in PHYSICAL_GATES, "physicalGate must be pending, passed, or failed")
    local_build = boolean(payload["localBuildSucceeded"], "localBuildSucceeded")
    mark_all = boolean(payload["markAllPhasesComplete"], "markAllPhasesComplete")
    unsupported = boolean(payload["unsupportedPhysicalClaim"], "unsupportedPhysicalClaim")
    claim_text = required_text(payload["claimText"], "claimText")
    software_result = required_text(payload["softwareResult"], "softwareResult")
    open_question = required_text(payload["openQuestion"], "openQuestion")
    evidence_kind = required_text(payload["evidenceKind"], "evidenceKind")
    require(
        evidence_kind in EVIDENCE_KINDS,
        "evidenceKind must be emulator, simulated, unavailable_probe, or host",
    )
    remote_commit = required_text(payload["remoteCommit"], "remoteCommit")

    rejected: list[str] = []
    # Narrower software result and the concurrent remote commit are both kept.
    preserved = [software_result, remote_commit]
    questions: list[str] = []
    if physical == "pending":
        questions.append(PENDING_QUESTION)
    if unsupported:
        rejected.append(claim_text)
        if open_question not in questions:
            questions.append(open_question)

    weak = evidence_kind in WEAK_EVIDENCE
    # localBuildSucceeded is never sufficient for completion. It also does not
    # veto a phase that otherwise meets the physical and host gates.
    qualified = (
        host == "passed"
        and physical == "passed"
        and not unsupported
        and not mark_all
        and not weak
    )
    if physical != "passed":
        decision = "software_verified_only" if host == "passed" else "blocked"
    elif host != "passed":
        decision = "blocked"
    elif qualified:
        decision = "complete"
    else:
        decision = "software_verified_only"

    if mark_all or local_build:
        qualifies_without_those_flags = (
            host == "passed"
            and physical == "passed"
            and not unsupported
            and not mark_all
            and not weak
        )
        if not qualifies_without_those_flags:
            require(decision != "complete", "local build or mark-all must not yield complete")
    if mark_all:
        require(decision != "complete", "marking every phase complete must not yield complete")
    if weak:
        require(decision != "complete", "weak evidence must not set decision complete")
    if unsupported:
        require(decision not in {"established", "complete"}, "unsupported physical claim")
    require(remote_commit in preserved, "remote commit dropped")
    require(software_result in preserved, "software result dropped")

    reasons: list[str] = []
    if decision == "software_verified_only":
        reasons.append(
            "Host gate passed; report software-verified only and do not invent completion."
        )
    elif decision == "blocked":
        reasons.append("Host gate did not pass; the phase is blocked.")
    else:
        reasons.append(
            "Host and physical gates passed without an unsupported physical claim "
            "or mark-all-phases mutation."
        )
    if physical == "pending":
        reasons.append("Physical device gate is pending.")
    elif physical == "failed":
        reasons.append("Physical device gate failed.")
    if unsupported:
        reasons.append(
            "Unsupported physical claim is rejected; the narrower software result is preserved."
        )
    if mark_all:
        reasons.append(
            "Marking every phase complete because the local build succeeded is rejected."
        )
    if local_build:
        reasons.append("Local build success must not mark phases complete.")
    if weak:
        reasons.append(f"Evidence kind {evidence_kind} cannot set decision complete.")
    return finish(decision, reasons, rejected, preserved, questions)
