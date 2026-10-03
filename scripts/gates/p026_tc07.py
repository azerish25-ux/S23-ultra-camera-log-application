"""TC-P026-07 cold-start recovery.

The process stops at a journal transition and relaunches without a clean
shutdown. Retained nonempty media is discovered conservatively and is not
called verified. Deleting every incomplete record on startup must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P026-07"
INTERVENTION = (
    "Terminate the process at a selected journal transition and relaunch without a clean shutdown."
)
EXPECTED = "Discover retained nonempty media conservatively and avoid claiming unfinished output is verified."
NEGATIVE = "Deleting every incomplete record on startup must fail."
TRANSITIONS = (
    "before_first_sample",
    "during_active_muxing",
    "during_finalization",
    "after_publication",
)
_PAYLOAD_KEYS = (
    "transition",
    "cleanShutdown",
    "mediaId",
    "mediaNonempty",
    "deletesIncomplete",
    "claimsVerified",
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
    """Keep incomplete media. Do not delete it or call it verified."""
    fields = _payload(payload)
    reasons = [INTERVENTION, f"transition {fields['transition']}"]
    preserved = [fields["mediaId"], "transition:" + fields["transition"]]
    if not fields["mediaNonempty"]:
        preserved.append("empty-media")
    rejected: list[str] = []
    if fields["deletesIncomplete"]:
        rejected.append("incomplete-records-deleted")
        reasons.append(NEGATIVE)
    if fields["claimsVerified"]:
        rejected.append("unfinished-claimed-verified")
        reasons.append("unfinished output was claimed verified")
    if rejected:
        decision = "rejected"
    elif fields["cleanShutdown"]:
        decision = "withheld"
        reasons.append("clean shutdown is not a cold-start relaunch")
    elif fields["mediaNonempty"]:
        decision = "retained_unverified"
        reasons.append(EXPECTED)
        reasons.append("retained media is not verified")
    else:
        decision = "withheld"
        reasons.append("no nonempty media was discovered")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    transition = payload["transition"]
    if transition not in TRANSITIONS:
        raise ValueError("transition is not a declared repeat")
    return {
        "transition": transition,
        "cleanShutdown": _bool(payload["cleanShutdown"], "cleanShutdown"),
        "mediaId": _token(payload["mediaId"], "mediaId"),
        "mediaNonempty": _bool(payload["mediaNonempty"], "mediaNonempty"),
        "deletesIncomplete": _bool(payload["deletesIncomplete"], "deletesIncomplete"),
        "claimsVerified": _bool(payload["claimsVerified"], "claimsVerified"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-07 must not yield qualified or allowed")
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
