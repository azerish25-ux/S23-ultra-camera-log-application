"""TC-P034-07 source mutation during development.

A noticed mutation stops publication and keeps the original id plus every
evidence token. An unnoticed change must not come back as a success.
"""

from __future__ import annotations

CASE_ID = "TC-P034-07"
INTERVENTION = "Alter the source or profile while a development job is reading it."
EXPECTED = (
    "Detect identity inconsistency, stop accepted publication, and preserve all "
    "available evidence without overwriting originals."
)
NEGATIVE = "A successful result whose source changed unnoticed must fail."

MUTATIONS = ("none", "renamed", "changed_bytes", "replaced_profile", "revoked_read")
_PAYLOAD_KEYS = ("mutation", "noticed", "originalId", "evidence")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "publication_stopped", "consistent"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop publication when a source mutation is noticed; never hide one."""
    mutation, noticed, original, evidence = _payload(payload)
    preserved = [f"original:{original}"]
    preserved.extend(f"evidence:{item}" for item in evidence)
    reasons = [INTERVENTION, EXPECTED]
    if mutation == "none":
        reasons.append("source identity was unchanged during the read")
        reasons.append("unchanged is not physical development acceptance")
        return _result("consistent", reasons, [], preserved, ["physical development unverified"])
    if not noticed:
        reasons.append(NEGATIVE)
        reasons.append(f"unnoticed {mutation} is not a successful result")
        return _result(
            "rejected",
            reasons,
            [f"unnoticed-mutation:{mutation}"],
            preserved,
            ["publication not accepted"],
        )
    reasons.append(f"noticed {mutation}; accepted publication stopped")
    reasons.append("original and evidence tokens were not overwritten")
    return _result(
        "publication_stopped",
        reasons,
        [],
        preserved,
        [f"stopped:{mutation}"],
    )


def _payload(payload: object) -> tuple[str, bool, str, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    mutation = payload["mutation"]
    if mutation not in MUTATIONS:
        raise ValueError("mutation is not a known kind")
    noticed = payload["noticed"]
    if type(noticed) is not bool:
        raise ValueError("noticed must be a bool")
    if mutation == "none" and not noticed:
        raise ValueError("an unchanged source has nothing unnoticed to report")
    original = payload["originalId"]
    if not isinstance(original, str) or not original or original != original.strip():
        raise ValueError("originalId must be a non-empty string")
    evidence = payload["evidence"]
    if (
        not isinstance(evidence, list)
        or not evidence
        or len(evidence) != len(set(evidence))
        or any(not isinstance(item, str) or not item or item != item.strip() for item in evidence)
    ):
        raise ValueError("evidence must be unique non-empty strings")
    return mutation, noticed, original, list(evidence)


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
