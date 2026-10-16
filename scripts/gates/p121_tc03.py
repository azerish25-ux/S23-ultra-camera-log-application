"""TC-P121-03 Checkpoint identity mismatch.

Host fixture. Resume is valid only when source, model, profile, and graph
match. Filename and frame number are not an identity.
"""

from __future__ import annotations


CASE_ID = "TC-P121-03"
NAME = "Checkpoint identity mismatch"
INTERVENTION = "Replace source, model, profile, or graph while retaining a previously completed chunk cache."
EXPECTED = "Reject incompatible resume data or start a distinct job with new identities."
NEGATIVE = "Filename and frame number alone must not validate a checkpoint."
REPEAT = "Repeat one changed identity field at a time and inspect specific rejection reasons."
NEGATIVE_TOKEN = "filename-and-frame-number-alone"
IDENTITY = ("source", "model", "profile", "graph")
REPEATS = IDENTITY
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "checkpointSource",
    "checkpointModel",
    "checkpointProfile",
    "checkpointGraph",
    "checkpointFilename",
    "checkpointFrame",
    "currentSource",
    "currentModel",
    "currentProfile",
    "currentGraph",
    "currentFilename",
    "currentFrame",
    "resumeRequested",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject a resume whose identity changed. Filename plus frame is not enough."""
    fields = _payload(payload)
    checkpoint = {
        "source": fields["checkpointSource"],
        "model": fields["checkpointModel"],
        "profile": fields["checkpointProfile"],
        "graph": fields["checkpointGraph"],
    }
    current = {
        "source": fields["currentSource"],
        "model": fields["currentModel"],
        "profile": fields["currentProfile"],
        "graph": fields["currentGraph"],
    }
    changed = [name for name in IDENTITY if checkpoint[name] != current[name]]
    filename_match = fields["checkpointFilename"] == fields["currentFilename"]
    frame_match = fields["checkpointFrame"] == fields["currentFrame"]
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if fields["resumeRequested"] and changed:
        for name in changed:
            rejected.append(f"checkpoint-{name}-mismatch")
            reasons.append(f"checkpoint {name} does not match the current job")
        if filename_match and frame_match:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    if not fields["resumeRequested"] and not changed:
        rejected.append("distinct-job-without-an-identity-change")
        reasons.append("a distinct job requires a new identity")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded" and changed:
        reasons.append("incompatible cache started a distinct job")
    if decision == "recorded" and not changed:
        reasons.append("checkpoint identity matched")
    preserved = [
        fields["evidenceId"],
        {
            "checkpoint": checkpoint,
            "current": current,
            "filename": fields["currentFilename"],
            "frame": fields["currentFrame"],
            "changed": changed,
            "resumeRequested": fields["resumeRequested"],
            "distinctJob": bool(changed) and not fields["resumeRequested"],
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _frame(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if type(payload["resumeRequested"]) is not bool:
        raise ValueError("resumeRequested must be a bool")
    parsed = {"evidenceId": _text(payload["evidenceId"], "evidenceId"), "repeat": repeat}
    for label in (
        "checkpointSource",
        "checkpointModel",
        "checkpointProfile",
        "checkpointGraph",
        "checkpointFilename",
        "currentSource",
        "currentModel",
        "currentProfile",
        "currentGraph",
        "currentFilename",
    ):
        parsed[label] = _text(payload[label], label)
    parsed["checkpointFrame"] = _frame(payload["checkpointFrame"], "checkpointFrame")
    parsed["currentFrame"] = _frame(payload["currentFrame"], "currentFrame")
    parsed["resumeRequested"] = payload["resumeRequested"]
    return parsed


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
