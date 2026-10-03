"""TC-P029-07 cold-start recovery.

Intervention: Terminate the process at a selected journal transition and
relaunch without a clean shutdown.
Expected: Discover retained nonempty media conservatively and avoid claiming
unfinished output is verified.
Negative: Deleting every incomplete record on startup must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P029-07"
INTERVENTION = (
    "Terminate the process at a selected journal transition and relaunch without a clean shutdown."
)
EXPECTED = (
    "Discover retained nonempty media conservatively and avoid claiming unfinished output is verified."
)
NEGATIVE = "Deleting every incomplete record on startup must fail."

_TRANSITIONS = (
    "before_first_sample",
    "active_muxing",
    "finalization",
    "after_publication",
)
_PAYLOAD_KEYS = (
    "transition",
    "cleanShutdown",
    "retainedMedia",
    "mediaNonempty",
    "deleteIncompleteOnStartup",
    "claimVerified",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "recovered_unverified", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Recover retained media without calling unfinished output verified."""
    transition, clean, media, nonempty, delete, claim = _payload(payload)
    preserved = [f"transition:{transition}", f"cleanShutdown:{str(clean).lower()}"]
    preserved.extend(media)

    rejected: list[str] = []
    if delete:
        rejected.append("incomplete-records-deleted")
    if claim:
        rejected.append("unfinished-output-claimed-verified")

    if rejected:
        decision = "rejected"
        questions = ["startup must not discard or verify unfinished output"]
        reasons = [EXPECTED]
        if delete:
            reasons.append(NEGATIVE)
        if claim:
            reasons.append("unfinished output is not verified")
        reasons.append("retained media names stay in the inventory")
    elif nonempty:
        decision = "recovered_unverified"
        questions = ["retained media is not a verified output"]
        reasons = [EXPECTED, "nonempty media discovered conservatively"]
        if not clean:
            reasons.append("relaunch had no clean shutdown")
    else:
        decision = "withheld"
        questions = ["no nonempty media discovered"]
        reasons = [EXPECTED, "absence of media is not a deletion of incomplete records"]

    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, bool, list[str], bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    transition = payload["transition"]
    if transition not in _TRANSITIONS:
        raise ValueError("transition is not a known journal transition")
    clean = _bool(payload["cleanShutdown"], "cleanShutdown")
    media = payload["retainedMedia"]
    if not isinstance(media, list) or len(media) != len(set(media)):
        raise ValueError("retainedMedia must be unique non-empty strings")
    if any(not isinstance(item, str) or not item for item in media):
        raise ValueError("retainedMedia must be unique non-empty strings")
    nonempty = _bool(payload["mediaNonempty"], "mediaNonempty")
    if nonempty != bool(media):
        raise ValueError("mediaNonempty must agree with retainedMedia")
    delete = _bool(payload["deleteIncompleteOnStartup"], "deleteIncompleteOnStartup")
    claim = _bool(payload["claimVerified"], "claimVerified")
    return transition, clean, list(media), nonempty, delete, claim


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("recovery decision cannot be qualified or allowed")
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
