"""TC-P125-03 Checkpoint identity mismatch.

Host fixture. Resume compares source, model, profile, and graph. Filename and
frame number alone do not validate a chunk cache.
"""

from __future__ import annotations


CASE_ID = "TC-P125-03"
NAME = "Checkpoint identity mismatch"
INTERVENTION = "Replace source, model, profile, or graph while retaining a previously completed chunk cache."
EXPECTED = "Reject incompatible resume data or start a distinct job with new identities."
NEGATIVE = "Filename and frame number alone must not validate a checkpoint."
REPEAT = "Repeat one changed identity field at a time and inspect specific rejection reasons."
FILENAME_TOKEN = "filename-and-frame-number-alone"
FIELDS = ("source", "model", "profile", "graph")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "changedField",
    "checkpointFilename",
    "checkpointFrame",
    "checkpointIdentity",
    "currentIdentity",
    "resumeAccepted",
    "distinctJob",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _identity(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise ValueError(f"{label} must contain source, model, profile, and graph")
    return {field: _text(value[field], f"{label}.{field}") for field in FIELDS}


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    changed = payload["changedField"]
    if repeat not in FIELDS:
        raise ValueError("repeat is unsupported")
    if changed not in ("none",) + FIELDS:
        raise ValueError("changedField is unsupported")
    if changed not in ("none", repeat):
        raise ValueError("repeat must name the changed field")
    filename = _text(payload["checkpointFilename"], "checkpointFilename")
    frame = payload["checkpointFrame"]
    if type(frame) is not int or frame < 0:
        raise ValueError("checkpointFrame must be a non-negative integer")
    if type(payload["resumeAccepted"]) is not bool or type(payload["distinctJob"]) is not bool:
        raise ValueError("resumeAccepted and distinctJob must be bools")
    checkpoint = _identity(payload["checkpointIdentity"], "checkpointIdentity")
    current = _identity(payload["currentIdentity"], "currentIdentity")
    differed = [field for field in FIELDS if checkpoint[field] != current[field]]
    if changed == "none":
        if differed:
            raise ValueError("identities differ")
    elif differed != [changed]:
        raise ValueError("repeat one changed identity field at a time")
    rejected: list[str] = []
    if differed and payload["resumeAccepted"]:
        rejected.append(FILENAME_TOKEN)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    if rejected:
        reasons.append(NEGATIVE)
        reasons.append("checkpoint filename and frame number were not sufficient")
    elif differed and payload["distinctJob"]:
        reasons.append("incompatible cache rejected; a distinct job carries the new identity")
    elif differed:
        reasons.append("incompatible resume data rejected")
    else:
        reasons.append("checkpoint identity matches the current job")
    preserved = [
        evidence,
        {
            "checkpointFilename": filename,
            "checkpointFrame": frame,
            "checkpointIdentity": checkpoint,
            "currentIdentity": current,
            "changedFields": differed,
            "resumeAccepted": payload["resumeAccepted"],
            "distinctJob": payload["distinctJob"],
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved)


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
