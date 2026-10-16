"""TC-P123-03 Checkpoint identity mismatch.

Host fixture. Resume requires source, model, profile, and graph identity.
Filename and frame number alone do not validate a checkpoint. A changed
identity starts a distinct job instead of reusing the chunk cache.
"""

from __future__ import annotations


CASE_ID = "TC-P123-03"
NAME = "Checkpoint identity mismatch"
INTERVENTION = "Replace source, model, profile, or graph while retaining a previously completed chunk cache."
EXPECTED = "Reject incompatible resume data or start a distinct job with new identities."
NEGATIVE = "Filename and frame number alone must not validate a checkpoint."
REPEAT = "Repeat one changed identity field at a time and inspect specific rejection reasons."
IDENTITY = ("sourceId", "modelId", "profileId", "graphId")
RECORD_KEYS = IDENTITY + ("filename", "frameNumber")
REPEATS = {"source": "sourceId", "model": "modelId", "profile": "profileId", "graph": "graphId"}
PAYLOAD_KEYS = ("evidenceId", "checkpoint", "current", "action", "repeat")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject a resume whose only agreement is filename and frame number."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    changed = [
        key for key in IDENTITY if fields["checkpoint"][key] != fields["current"][key]
    ]
    filename_and_frame = (
        fields["checkpoint"]["filename"] == fields["current"]["filename"]
        and fields["checkpoint"]["frameNumber"] == fields["current"]["frameNumber"]
    )
    if fields["action"] == "resume" and changed:
        rejected.append("checkpoint-identity-mismatch")
        reasons.append("incompatible resume data for " + ",".join(changed))
        if filename_and_frame:
            rejected.append("filename-and-frame-number-alone")
            reasons.append(NEGATIVE)
    if fields["action"] == "distinct-job" and not changed:
        rejected.append("distinct-job-without-new-identity")
        reasons.append("a distinct job requires a new identity")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        if fields["action"] == "resume":
            reasons.append("checkpoint identity matches the current job")
        else:
            reasons.append("distinct job started with a new identity")
    preserved = [
        fields["evidenceId"],
        {"checkpoint": dict(fields["checkpoint"]), "current": dict(fields["current"])},
        {"changed": changed, "filenameAndFrameMatch": filename_and_frame, "action": fields["action"]},
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _record(value: object, label: str) -> dict:
    if not isinstance(value, dict) or set(value) != set(RECORD_KEYS):
        raise ValueError(f"{label} keys are invalid")
    record = {}
    for key in IDENTITY + ("filename",):
        item = value[key]
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{label}.{key} must be a non-empty string")
        record[key] = item
    frame = value["frameNumber"]
    if type(frame) is not int or frame < 0:
        raise ValueError(f"{label}.frameNumber must be a non-negative integer")
    record["frameNumber"] = frame
    return record


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    action = payload["action"]
    if action not in {"resume", "distinct-job"}:
        raise ValueError("action must be resume or distinct-job")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    checkpoint = _record(payload["checkpoint"], "checkpoint")
    current = _record(payload["current"], "current")
    field = REPEATS[repeat]
    changed = [key for key in IDENTITY if checkpoint[key] != current[key]]
    if changed not in ([], [field]):
        raise ValueError("repeat must change exactly one identity field or none")
    return {
        "evidenceId": evidence,
        "checkpoint": checkpoint,
        "current": current,
        "action": action,
        "repeat": repeat,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
