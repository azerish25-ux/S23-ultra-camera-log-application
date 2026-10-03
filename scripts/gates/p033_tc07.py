"""TC-P033-07 source mutation during development.

If the source or profile changes while a development job is reading it, the
job stops publication and keeps the evidence it already has. A successful
result that did not notice the change is rejected. Originals are not overwritten.
"""

from __future__ import annotations

CASE_ID = "TC-P033-07"
INTERVENTION = "Alter the source or profile while a development job is reading it."
EXPECTED = (
    "Detect identity inconsistency, stop accepted publication, and preserve all available "
    "evidence without overwriting originals."
)
NEGATIVE = "A successful result whose source changed unnoticed must fail."
REPEATS = ("renamed files", "changed bytes", "replaced profiles", "revoked read access")
_MUTATIONS = ("none", "renamed", "changed-bytes", "replaced-profile", "revoked-read")
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


def evaluate(payload: dict) -> dict:
    """Stop publication when the source identity moves under the reader."""
    data = _payload(payload)
    mutation = data["mutation"]
    reasons = ["mutation " + mutation]
    rejected: list[str] = []
    unnoticed_success = mutation != "none" and not data["noticed"] and data["published"]
    if unnoticed_success:
        rejected.append("unnoticed-source-change")
        reasons.append(NEGATIVE)
    if data["overwriteOriginal"]:
        rejected.append("original-overwritten")
        reasons.append("originals must not be overwritten")
    if mutation != "none" and data["noticed"] and data["published"] and not unnoticed_success:
        rejected.append("published-after-mutation")
        reasons.append("publication stops when identity changes")
    if mutation != "none":
        rejected.append("identity-" + mutation)
    if unnoticed_success or data["overwriteOriginal"] or (mutation != "none" and data["published"]):
        decision = "rejected"
        reasons.append(EXPECTED)
    elif mutation != "none":
        decision = "publication_stopped"
        reasons.append(EXPECTED)
        reasons.append("publication_stopped is not a successful development result")
    elif data["published"]:
        decision = "consistent_read"
        reasons.append("the read identity stayed consistent")
        reasons.append("consistent_read is not physical qualification")
    else:
        decision = "read_open"
        reasons.append("no mutation was observed and nothing was published")
    if mutation == "none":
        rejected = [item for item in rejected if item == "original-overwritten"]
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-07 must not yield qualified or allowed")
    if unnoticed_success and decision != "rejected":
        raise ValueError("an unnoticed source change must not succeed")
    questions = ["original bytes were kept"] if not data["overwriteOriginal"] else ["overwrite was refused by this gate"]
    return _result(decision, reasons, rejected, list(data["evidence"]), questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    mutation = payload["mutation"]
    if mutation not in _MUTATIONS:
        raise ValueError("mutation is not in the host vocabulary")
    noticed = _bool(payload["noticed"], "noticed")
    if mutation == "none" and noticed:
        raise ValueError("a noticed mutation requires a mutation kind")
    return {
        "mutation": mutation,
        "noticed": noticed,
        "published": _bool(payload["published"], "published"),
        "overwriteOriginal": _bool(payload["overwriteOriginal"], "overwriteOriginal"),
        "evidence": _tokens(payload["evidence"], "evidence"),
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    items = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip() or item in seen:
            raise ValueError(f"{name} items must be unique non-empty strings")
        seen.add(item)
        items.append(item)
    return items


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-07 must not yield qualified or allowed")
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
