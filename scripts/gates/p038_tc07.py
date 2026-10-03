"""TC-P038-07 source mutation during development.

Intervention: Alter the source or profile while a development job is reading it.
Expected: Detect identity inconsistency, stop accepted publication, and preserve
all available evidence without overwriting originals.
Negative: A successful result whose source changed unnoticed must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P038-07"
INTERVENTION = "Alter the source or profile while a development job is reading it."
EXPECTED = (
    "Detect identity inconsistency, stop accepted publication, and preserve all "
    "available evidence without overwriting originals."
)
NEGATIVE = "A successful result whose source changed unnoticed must fail."

_MUTATIONS = ("none", "renamed", "changed-bytes", "replaced-profile", "revoked-read")
_PAYLOAD_KEYS = (
    "originalId",
    "observedId",
    "mutation",
    "unnoticedSuccess",
    "evidenceTokens",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "stopped", "consistent")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop publication when the source identity moves. Keep every evidence token."""
    original, observed, mutation, unnoticed, evidence = _payload(payload)
    preserved = [original, f"observed:{observed}"]
    preserved.extend(evidence)
    if unnoticed and mutation != "none":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "publication was not accepted"],
            ["unnoticed-source-change", mutation],
            preserved,
            ["accepted publication stopped"],
        )
    if mutation == "none":
        return _result(
            "consistent",
            [EXPECTED, "identity stayed consistent", "consistency is not physical qualification"],
            [],
            preserved,
            ["not a physical qualification"],
        )
    questions = ["accepted publication stopped"]
    if mutation == "revoked-read":
        questions.append("read access revoked")
    return _result(
        "stopped",
        [EXPECTED, f"identity inconsistency:{mutation}", "originals were not overwritten"],
        [mutation],
        preserved,
        questions,
    )


def _payload(payload: object) -> tuple[str, str, str, bool, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    original = _text(payload["originalId"], "originalId")
    observed = _text(payload["observedId"], "observedId")
    mutation = payload["mutation"]
    if mutation not in _MUTATIONS:
        raise ValueError("mutation is not a known kind")
    unnoticed = payload["unnoticedSuccess"]
    if type(unnoticed) is not bool:
        raise ValueError("unnoticedSuccess must be a bool")
    if unnoticed and mutation == "none":
        raise ValueError("unnoticed success requires a mutation")
    if mutation == "none" and observed != original:
        raise ValueError("consistent identity cannot rename the source")
    if mutation == "renamed" and observed == original:
        raise ValueError("renamed mutation must change the id")
    evidence = payload["evidenceTokens"]
    if type(evidence) is not list or not evidence:
        raise ValueError("evidenceTokens must be a non-empty list")
    if any(type(item) is not str or not item for item in evidence):
        raise ValueError("evidenceTokens must be non-empty strings")
    return original, observed, mutation, unnoticed, list(evidence)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(label + " must be a non-empty string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("mutation decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
