"""TC-P040-07 source mutation during development.

Intervention: Alter the source or profile while a development job is reading it.
Expected: Detect identity inconsistency, stop accepted publication, and preserve
all available evidence without overwriting originals.
Negative: A successful result whose source changed unnoticed must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P040-07"
INTERVENTION = "Alter the source or profile while a development job is reading it."
EXPECTED = (
    "Detect identity inconsistency, stop accepted publication, and preserve all available "
    "evidence without overwriting originals."
)
NEGATIVE = "A successful result whose source changed unnoticed must fail."

_MUTATIONS = ("none", "renamed", "changed_bytes", "replaced_profile", "revoked_read")
_PAYLOAD_KEYS = (
    "mutation",
    "noticed",
    "published",
    "overwriteOriginal",
    "evidence",
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
    """Stop publication when a source changes. Keep every evidence token."""
    fields = _payload(payload)
    preserved = list(fields["evidence"])
    mutation = fields["mutation"]
    rejected: list[str] = []
    questions: list[str] = []
    if fields["overwriteOriginal"]:
        rejected.append("overwrite-original")
    if mutation != "none" and not fields["noticed"]:
        rejected.append("unnoticed-source-change")
        rejected.append(mutation)
    if mutation != "none" and fields["published"]:
        rejected.append("published-after-mutation")
        if mutation not in rejected:
            rejected.append(mutation)
    if rejected:
        decision = "rejected"
        reasons = [EXPECTED, "accepted publication stopped"]
        if "unnoticed-source-change" in rejected:
            reasons.insert(0, NEGATIVE)
        if "overwrite-original" in rejected:
            reasons.append("originals were not overwritten")
        questions.append("evidence preserved")
    elif mutation != "none":
        decision = "stopped"
        rejected.append(mutation)
        reasons = [
            EXPECTED,
            f"identity inconsistency {mutation} detected",
            "accepted publication stopped",
        ]
        questions.append("publication stopped")
    else:
        decision = "consistent"
        reasons = [
            "source identity held while the job was reading",
            "this consistent read is not a qualified publication",
        ]
        if fields["published"]:
            reasons.append("publication matched the evidence that was read")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    mutation = payload["mutation"]
    if mutation not in _MUTATIONS:
        raise ValueError("mutation is not a known change")
    noticed = payload["noticed"]
    published = payload["published"]
    overwrite = payload["overwriteOriginal"]
    if type(noticed) is not bool or type(published) is not bool or type(overwrite) is not bool:
        raise ValueError("noticed, published, and overwriteOriginal must be bools")
    evidence = payload["evidence"]
    if not isinstance(evidence, list) or not evidence or len(evidence) != len(set(evidence)):
        raise ValueError("evidence must be unique non-empty strings")
    if any(not isinstance(item, str) or not item for item in evidence):
        raise ValueError("evidence must be unique non-empty strings")
    return {
        "mutation": mutation,
        "noticed": noticed,
        "published": published,
        "overwriteOriginal": overwrite,
        "evidence": list(evidence),
    }


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
