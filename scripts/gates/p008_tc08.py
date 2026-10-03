"""TC-P008-08 independent reproduction.

A host gate can software-verify only while the physical device gate is
pending. Undocumented files, unrecorded manual steps, and missing
prerequisites stay unverified. A connected phone does not certify the
device. Temporary paths are ignored. Completion is not invented.
"""

from __future__ import annotations

CASE_ID = "TC-P008-08"

_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_PAYLOAD_KEYS = (
    "reproduction",
    "statedSoftwareResult",
    "tempPath",
    "remoteCommit",
    "hostGatePassed",
    "physicalGate",
)

_REPRODUCTION_KEYS = (
    "undocumentedFiles",
    "manualIntervention",
    "missingPrerequisite",
    "phoneConnected",
)

_PHYSICAL_GATES = ("pending", "passed")


def evaluate(payload: object) -> dict:
    """Judge an independent reproduction attempt.

    Returns exactly caseId, decision, reasons, rejectedClaims,
    preservedResults, and openQuestions. Raises ValueError if payload is
    invalid. reasons is non-empty because this case never decides "allowed".
    tempPath is accepted and ignored.
    """
    data = _payload(payload)
    reproduction = data["reproduction"]
    undocumented = reproduction["undocumentedFiles"]
    manual = reproduction["manualIntervention"]
    prerequisite = reproduction["missingPrerequisite"]
    phone_connected = reproduction["phoneConnected"]
    stated = data["statedSoftwareResult"]
    remote_commit = data["remoteCommit"]
    host_passed = data["hostGatePassed"]
    physical_gate = data["physicalGate"]
    # tempPath must not affect the decision or the preserved record.
    _ = data["tempPath"]

    preserved = {
        "statedSoftwareResult": stated,
        "remoteCommit": remote_commit,
    }
    dirty = undocumented or manual or prerequisite is not None

    if dirty:
        decision = "unverified"
        reasons = []
        rejected = []
        open_questions: list[str] = []
        if undocumented:
            reasons.append(
                "reproduction depends on undocumented files and stays unverified"
            )
            rejected.append("undocumented-files")
            open_questions.append("undocumented files block reproduction")
        if manual:
            reasons.append(
                "reproduction depends on an unrecorded manual intervention and stays unverified"
            )
            rejected.append("unrecorded-manual-intervention")
            open_questions.append("unrecorded manual intervention blocks reproduction")
        if prerequisite is not None:
            reasons.append(f"missing prerequisite: {prerequisite}")
            rejected.append("missing-prerequisite")
            open_questions.append(prerequisite)
        reasons.append("completion is not invented")
        if host_passed and physical_gate == "passed":
            reasons.append(
                "host and physical gates do not verify a reproduction that is not self-contained"
            )
        if phone_connected:
            reasons.append("a connected phone does not certify the physical device gate")
    elif not host_passed:
        decision = "blocked"
        reasons = [
            "host gate has not passed",
            "stated software result is not reported as reproduced",
            "remote commit is preserved",
            "completion is not invented",
        ]
        if physical_gate == "pending":
            reasons.append(
                "physical device gate pending does not upgrade a failed host gate"
            )
        else:
            reasons.append(
                "a passed physical gate does not verify software when the host gate failed"
            )
        if phone_connected:
            reasons.append("a connected phone does not certify the physical device gate")
        rejected = ["host-gate-not-passed"]
        open_questions = ["host gate has not passed"]
    elif physical_gate == "pending":
        decision = "software_verified_only"
        reasons = [
            "host gate passed",
            "physical device gate is pending so the result is software-verified only",
            "remote commit is preserved",
            "completion is not invented",
        ]
        if phone_connected:
            reasons.append("a connected phone does not certify the physical device gate")
        else:
            reasons.append(
                "phone connection is not required and does not change the pending physical gate"
            )
        rejected = []
        open_questions = ["physical device gate pending"]
    else:
        decision = "reproduced"
        reasons = [
            "stated software result was reproduced",
            "host gate passed",
            "physical device gate passed",
            "remote commit is preserved",
        ]
        if phone_connected:
            reasons.append(
                "phone connection was not required to accept the recorded physical gate"
            )
        rejected = []
        open_questions = []

    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if type(payload) is not dict:
        raise ValueError("payload must be a dict")
    missing = [key for key in _PAYLOAD_KEYS if key not in payload]
    extra = [key for key in payload if key not in _PAYLOAD_KEYS]
    if missing or extra:
        raise ValueError(
            "payload keys are invalid:"
            f" missing={missing or '[]'} extra={extra or '[]'}"
        )
    reproduction = payload["reproduction"]
    if type(reproduction) is not dict:
        raise ValueError("reproduction must be a dict")
    r_missing = [key for key in _REPRODUCTION_KEYS if key not in reproduction]
    r_extra = [key for key in reproduction if key not in _REPRODUCTION_KEYS]
    if r_missing or r_extra:
        raise ValueError(
            "reproduction keys are invalid:"
            f" missing={r_missing or '[]'} extra={r_extra or '[]'}"
        )
    for flag in ("undocumentedFiles", "manualIntervention", "phoneConnected"):
        if type(reproduction[flag]) is not bool:
            raise ValueError(f"reproduction.{flag} must be a bool")
    prerequisite = reproduction["missingPrerequisite"]
    if prerequisite is not None and (
        type(prerequisite) is not str or prerequisite.strip() == ""
    ):
        raise ValueError("missingPrerequisite must be a non-empty string or None")
    stated = payload["statedSoftwareResult"]
    if type(stated) is not str or stated.strip() == "":
        raise ValueError("statedSoftwareResult must be a non-empty string")
    if type(payload["tempPath"]) is not str:
        raise ValueError("tempPath must be a string")
    commit = payload["remoteCommit"]
    if type(commit) is not str or commit.strip() == "":
        raise ValueError("remoteCommit must be a non-empty string")
    if type(payload["hostGatePassed"]) is not bool:
        raise ValueError("hostGatePassed must be a bool")
    physical = payload["physicalGate"]
    if physical not in _PHYSICAL_GATES:
        raise ValueError("physicalGate must be 'pending' or 'passed'")
    return payload


def _result(decision, reasons, rejected, preserved, open_questions) -> dict:
    if decision in ("complete", "allowed"):
        raise ValueError("completion must not be invented")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": dict(preserved),
        "openQuestions": list(open_questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("result keys are invalid")
    return result
