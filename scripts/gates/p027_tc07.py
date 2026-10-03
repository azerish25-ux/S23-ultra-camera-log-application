"""TC-P027-07 cold-start recovery.

The process dies at a journal transition and relaunches without a clean
shutdown. Retained nonempty media is discovered and not called verified.
Deleting every incomplete record on startup must fail.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-07"
INTERVENTION = "Terminate the process at a selected journal transition and relaunch without a clean shutdown."
EXPECTED = "Discover retained nonempty media conservatively and avoid claiming unfinished output is verified."
NEGATIVE = "Deleting every incomplete record on startup must fail."
TRANSITIONS = (
    "before-first-sample",
    "during-active-muxing",
    "during-finalization",
    "after-publication",
)
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_PAYLOAD_KEYS = {
    "transition",
    "deletedIncomplete",
    "knownRecords",
    "claimedVerified",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Discover retained media. Do not delete incomplete records or call them verified."""
    data = _payload(payload)
    reasons = [f"transition {data['transition']}", INTERVENTION]
    preserved = list(data["knownRecords"]) + [data["transition"]]
    rejected: list[str] = []
    questions: list[str] = []
    if data["deletedIncomplete"]:
        rejected.append("incomplete-records-deleted")
        reasons.append(NEGATIVE)
    if data["claimedVerified"]:
        rejected.append("unfinished-claimed-verified")
        reasons.append("unfinished output was claimed verified")
    if rejected:
        decision = "rejected"
    elif not data["knownRecords"]:
        decision = "withheld"
        questions.append("no nonempty media discovered")
        reasons.append("cold start found no retained media")
    else:
        decision = "discovered"
        reasons.append(EXPECTED)
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    transition = payload["transition"]
    if transition not in TRANSITIONS:
        raise ValueError("transition is not a declared journal point")
    records = payload["knownRecords"]
    if not isinstance(records, list):
        raise ValueError("knownRecords must be a list")
    parsed = []
    for item in records:
        if not isinstance(item, str) or _TOKEN.fullmatch(item) is None:
            raise ValueError("knownRecords entries must be tokens")
        parsed.append(item)
    if len(parsed) != len(set(parsed)):
        raise ValueError("knownRecords must be unique")
    return {
        "transition": transition,
        "deletedIncomplete": _bool(payload["deletedIncomplete"], "deletedIncomplete"),
        "knownRecords": parsed,
        "claimedVerified": _bool(payload["claimedVerified"], "claimedVerified"),
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-07 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
