"""TC-P121-04 Cancellation at acceptance boundary.

Host fixture. Cancellation is acknowledged only after ownership is controlled.
A cancelled job is never published as accepted, and a late worker callback
cannot reverse the cancellation.
"""

from __future__ import annotations


CASE_ID = "TC-P121-04"
NAME = "Cancellation at acceptance boundary"
INTERVENTION = "Cancel during rendering, verification, publication, or final cleanup."
EXPECTED = "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted."
NEGATIVE = "A late worker callback that reverses cancellation must fail."
REPEAT = "Repeat with process restart and an already retained partial output."
LATE_TOKEN = "late-worker-callback-reverses-cancellation"
PUBLISH_TOKEN = "cancelled-job-published-as-accepted"
OWNERSHIP_TOKEN = "cancellation-acknowledged-before-ownership"
REPEATS = ("process-restart", "retained-partial")
STAGES = ("rendering", "verification", "publication", "final-cleanup")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "stage",
    "cancelRequested",
    "ownershipControlled",
    "acknowledged",
    "lateCallbackReversesCancel",
    "publishedAsAccepted",
    "partialOutputRetained",
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
    """Acknowledge cancel only with ownership. Never accept a cancelled publish."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", f"stage {fields['stage']}"]
    if fields["lateCallbackReversesCancel"]:
        rejected.append(LATE_TOKEN)
        reasons.append(NEGATIVE)
    if fields["cancelRequested"] and fields["publishedAsAccepted"]:
        rejected.append(PUBLISH_TOKEN)
        reasons.append("a cancelled job was not published as accepted")
    if fields["acknowledged"] and not fields["ownershipControlled"]:
        rejected.append(OWNERSHIP_TOKEN)
        reasons.append("cancellation was acknowledged before ownership was controlled")
    if fields["acknowledged"] and not fields["cancelRequested"]:
        rejected.append("acknowledged-without-cancellation")
        reasons.append("acknowledgement requires a cancellation")
    if fields["publishedAsAccepted"] and not fields["cancelRequested"] and fields["stage"] != "publication":
        rejected.append("accepted-outside-publication")
        reasons.append("acceptance is only meaningful at publication")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded" and fields["cancelRequested"]:
        reasons.append("cancellation acknowledged under ownership and not accepted")
    if decision == "recorded" and not fields["cancelRequested"]:
        reasons.append("job was not cancelled")
    preserved = [
        fields["evidenceId"],
        {
            "stage": fields["stage"],
            "cancelRequested": fields["cancelRequested"],
            "ownershipControlled": fields["ownershipControlled"],
            "acknowledged": fields["acknowledged"] and fields["ownershipControlled"] and fields["cancelRequested"],
            "publishedAsAccepted": False if fields["cancelRequested"] else fields["publishedAsAccepted"],
            "partialOutputRetained": fields["partialOutputRetained"],
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    stage = payload["stage"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if stage not in STAGES:
        raise ValueError("stage is unsupported")
    flags = {}
    for label in (
        "cancelRequested",
        "ownershipControlled",
        "acknowledged",
        "lateCallbackReversesCancel",
        "publishedAsAccepted",
        "partialOutputRetained",
    ):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
        flags[label] = payload[label]
    return {
        "evidenceId": _text(payload["evidenceId"], "evidenceId"),
        "repeat": repeat,
        "stage": stage,
        **flags,
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
