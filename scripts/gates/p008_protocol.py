#!/usr/bin/env python3
"""P008 host gate for the agent operating protocol and handoff schema.

The assessor separates a host-gate result from physical-device qualification.
It does not execute TC-P008-01..08, talk to a phone, or treat a local build as
completion of the programme. A missing push credential or an unverified remote
head blocks publication. A concurrent remote commit is preserved either way.
"""

from __future__ import annotations

import re
from typing import Any


HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
PHASE_ID = re.compile(r"^P[0-9]{3}$")

PROTOCOL_KEYS = {
    "schemaVersion",
    "phase",
    "protocolId",
    "implementationBaseRevision",
    "steps",
    "publication",
    "completionRule",
}
PUBLICATION_KEYS = {"branch", "fastForwardOnly", "verifyRemoteHead", "blockedWithoutAccess"}
HANDOFF_FIELDS = (
    "phase",
    "caseIds",
    "changedFiles",
    "commit",
    "testsRun",
    "failures",
    "unverified",
    "nextPhase",
)
REPORT_KEYS = {
    "hostGate",
    "physicalGate",
    "localBuildSucceeded",
    "markAllPhasesComplete",
    "remoteCommit",
    "remoteHeadVerified",
    "accessAbsent",
}
IMPLEMENTATION_BASE = "fffd5c9a63cb732e103052acae29ae0c251585cc"
COMPLETION_RULE = "host and physical gates are separate; local build is not phase completion"
STEP_MARKERS = (
    "dependency-ready",
    "failing test",
    "smallest correct change",
    "record evidence",
    "existing branch",
    "remote head",
    "access is absent",
    "software-verified only",
    "remote commit",
    "local build",
)
LOCAL_BUILD_CLAIM = "local-build-completes-programme"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: dict, required: set[str], context: str) -> None:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))


def _nonempty_strings(value: object, context: str, *, allow_empty: bool) -> None:
    require(isinstance(value, list), context + " must be a list")
    if not allow_empty:
        require(len(value) > 0, context + " must be a non-empty list")
    for item in value:
        require(isinstance(item, str) and bool(item.strip()), context + " entries must be non-empty strings")


def _ordered_markers(steps: list[str], markers: tuple[str, ...]) -> None:
    cursor = -1
    for marker in markers:
        found = None
        for index in range(cursor + 1, len(steps)):
            if marker in steps[index].lower():
                found = index
                break
        require(found is not None, "steps omit or reorder required action: " + marker)
        cursor = found


def validate_protocol(protocol: dict) -> None:
    """Raise ValueError unless protocol is the P008 operating protocol."""
    exact_keys(protocol, PROTOCOL_KEYS, "protocol")
    require(type(protocol["schemaVersion"]) is int and protocol["schemaVersion"] == 1, "Unsupported protocol schema")
    require(protocol["phase"] == "P008", "Protocol phase must be P008")
    require(protocol["protocolId"] == "s23-agent-protocol", "Unexpected protocol id")
    require(protocol["implementationBaseRevision"] == IMPLEMENTATION_BASE, "Unexpected implementation base revision")
    require(protocol["completionRule"] == COMPLETION_RULE, "Unexpected completion rule")
    steps = protocol["steps"]
    require(isinstance(steps, list) and len(steps) >= len(STEP_MARKERS), "Protocol steps are incomplete")
    require(all(isinstance(step, str) and step.strip() for step in steps), "Protocol steps must be non-empty strings")
    _ordered_markers(steps, STEP_MARKERS)
    joined = "\n".join(steps).lower()
    for phrase in ("main", "fast-forward", "blocked", "physical", "failing test"):
        require(phrase in joined, "Protocol steps do not cover " + phrase)
    publication = protocol["publication"]
    exact_keys(publication, PUBLICATION_KEYS, "publication")
    require(publication["branch"] == "main", "Publication branch must be main")
    require(publication["fastForwardOnly"] is True, "Publication must be fast-forward only")
    require(publication["verifyRemoteHead"] is True, "Publication must verify the remote head")
    require(publication["blockedWithoutAccess"] is True, "Publication must block when access is absent")


def validate_handoff(handoff: dict) -> None:
    """Raise ValueError unless handoff has exactly the schema fields and legal values.

    commit is 40 hex characters, or null only when nextPhase is blocked.
    testsRun is a non-empty list. unverified is a list. nextPhase is P009-style
    or the string blocked.
    """
    exact_keys(handoff, set(HANDOFF_FIELDS), "handoff")
    require(isinstance(handoff["phase"], str) and PHASE_ID.fullmatch(handoff["phase"]) is not None,
            "phase must look like P008")
    _nonempty_strings(handoff["caseIds"], "caseIds", allow_empty=True)
    _nonempty_strings(handoff["changedFiles"], "changedFiles", allow_empty=True)
    _nonempty_strings(handoff["testsRun"], "testsRun", allow_empty=False)
    _nonempty_strings(handoff["failures"], "failures", allow_empty=True)
    require(isinstance(handoff["unverified"], list), "unverified must be a list")
    for item in handoff["unverified"]:
        require(isinstance(item, str), "unverified entries must be strings")
    next_phase = handoff["nextPhase"]
    require(isinstance(next_phase, str), "nextPhase must be a string")
    blocked = next_phase == "blocked"
    require(blocked or PHASE_ID.fullmatch(next_phase) is not None, "nextPhase must look like P009 or blocked")
    commit = handoff["commit"]
    if commit is None:
        require(blocked, "commit may be null only when the handoff is blocked")
    else:
        require(isinstance(commit, str) and HEX40.fullmatch(commit) is not None,
                "commit must be 40 hex characters or null if blocked")


def _commit_present(remote_commit: object) -> bool:
    return isinstance(remote_commit, str) and remote_commit != ""


def assess_completion(report: dict) -> dict:
    """Classify a phase report without inventing programme completion.

    Precedence:
    1. accessAbsent -> blocked, and reasons mention no push access.
    2. A passed host gate with a physical gate that is not passed is
       software_verified_only. markAllPhasesComplete, or a successful local
       build while the physical gate is not passed, is software_verified_only
       when the host gate passed and blocked otherwise.
    3. remoteHeadVerified false while a remote commit is present -> blocked,
       unless a decision was already returned above.
    4. Host passed, physical passed, remote head verified, completion not
       invented, and access present -> complete.
    remoteCommit is copied into preservedResults whenever it is a non-empty string.
    """
    exact_keys(report, REPORT_KEYS, "completion report")
    host = report["hostGate"]
    physical = report["physicalGate"]
    local_build = report["localBuildSucceeded"]
    mark_all = report["markAllPhasesComplete"]
    remote_commit = report["remoteCommit"]
    remote_verified = report["remoteHeadVerified"]
    access_absent = report["accessAbsent"]
    require(isinstance(host, str) and bool(host.strip()), "hostGate must be a non-empty string")
    require(isinstance(physical, str) and bool(physical.strip()), "physicalGate must be a non-empty string")
    require(type(local_build) is bool, "localBuildSucceeded must be a boolean")
    require(type(mark_all) is bool, "markAllPhasesComplete must be a boolean")
    require(remote_commit is None or isinstance(remote_commit, str), "remoteCommit must be a string or null")
    require(type(remote_verified) is bool, "remoteHeadVerified must be a boolean")
    require(type(access_absent) is bool, "accessAbsent must be a boolean")

    commit_present = _commit_present(remote_commit)
    preserved: dict[str, Any] = {}
    if commit_present:
        preserved["remoteCommit"] = remote_commit
    if host == "passed":
        preserved["hostGate"] = "passed"

    rejected: list[str] = []
    if mark_all:
        rejected.append(LOCAL_BUILD_CLAIM)

    open_questions: list[str] = []
    if physical != "passed":
        open_questions.append("physical device gate remains open; this is not a physical S23 qualification")
    if access_absent:
        open_questions.append("push access is absent")
    if commit_present and not remote_verified:
        open_questions.append("remote head has not been verified")

    false_completion = mark_all or (local_build and physical != "passed")
    host_without_physical = host == "passed" and physical != "passed"
    reasons: list[str] = []

    if access_absent:
        decision = "blocked"
        reasons.append("no push access")
    elif host_without_physical or (false_completion and host == "passed"):
        decision = "software_verified_only"
        reasons.append(
            "host gate passed; physical gate is separate and local build success is not phase completion"
        )
        if commit_present and not remote_verified:
            reasons.append("remote head must be verified before an authorized push")
    elif false_completion:
        decision = "blocked"
        reasons.append("host gate has not passed; local build success is not phase completion")
    elif commit_present and not remote_verified:
        decision = "blocked"
        reasons.append("remote head must be verified before an authorized push")
    elif host == "passed" and physical == "passed" and remote_verified and not mark_all and not access_absent:
        decision = "complete"
        reasons.append("host and physical gates passed and the remote head was verified")
    else:
        decision = "blocked"
        if host != "passed":
            reasons.append("host gate has not passed")
        elif not remote_verified:
            reasons.append("remote head must be verified before an authorized push")
        else:
            reasons.append("completion conditions are not met")

    return {
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
