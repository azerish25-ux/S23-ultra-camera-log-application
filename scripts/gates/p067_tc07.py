"""TC-P067-07 graphics context loss.

Intervention: Invalidate the backend context or surface during initialization,
rendering, or cleanup.
Expected: Reach a defined recovery or failure state without publishing
unverified frames or leaking resources.
Negative: Using stale handles after context recreation must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P067-07"
INTERVENTION = "Invalidate the backend context or surface during initialization, rendering, or cleanup."
EXPECTED = "Reach a defined recovery or failure state without publishing unverified frames or leaking resources."
NEGATIVE = "Using stale handles after context recreation must fail."
REPEAT = "Repeat with retained source availability and a queued development job."

_PHASES = ("initialization", "rendering", "cleanup")
_SITES = ("baseline", "source-retained", "queued-job")
_STATES = ("recovered", "failed", "undefined")
_PAYLOAD_KEYS = (
    "phase",
    "site",
    "contextInvalid",
    "staleHandles",
    "publishedUnverified",
    "leaked",
    "state",
    "sourceRetained",
    "queuedJob",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "defined_state"}
_TOKEN = re.compile(r"^[a-z-]+$")


def evaluate(payload: dict) -> dict:
    """Reach a defined state, or reject stale handles after recreation."""
    phase, site, invalid, stale, unverified, leaked, state, source, queued = _payload(payload)
    preserved = [
        f"phase:{phase}",
        f"site:{site}",
        f"state:{state}",
        f"source:{str(source).lower()}",
        f"queued:{str(queued).lower()}",
        f"context-invalid:{str(invalid).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"site {site}"]
    rejected: list[str] = []
    if stale:
        rejected.append("stale-handles")
        reasons.append(NEGATIVE)
        reasons.append(f"{phase} reused a stale handle after context recreation")
    if unverified:
        rejected.append("unverified-frames")
        reasons.append(f"{phase} published an unverified frame")
    if leaked:
        rejected.append("resource-leak")
        reasons.append(f"{phase} leaked a resource")
    if state == "undefined":
        rejected.append("undefined-state")
        reasons.append(f"{phase} did not reach a defined recovery or failure state")
    if rejected:
        decision = "rejected"
        questions.append("source availability and queued job were retained")
    elif not invalid:
        decision = "withheld"
        reasons.append(f"{phase} context was not invalidated")
        questions.append("no unverified frame was published")
    elif state in {"recovered", "failed"}:
        decision = "defined_state"
        reasons.append(f"{phase} reached defined state {state}")
    else:
        decision = "rejected"
        rejected.append("undefined-state")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    phase = payload["phase"]
    if phase not in _PHASES:
        raise ValueError("phase is unsupported")
    site = payload["site"]
    if not isinstance(site, str) or _TOKEN.fullmatch(site) is None or site not in _SITES:
        raise ValueError("site is unsupported")
    invalid = payload["contextInvalid"]
    stale = payload["staleHandles"]
    unverified = payload["publishedUnverified"]
    leaked = payload["leaked"]
    source = payload["sourceRetained"]
    queued = payload["queuedJob"]
    for name, value in (
        ("contextInvalid", invalid),
        ("staleHandles", stale),
        ("publishedUnverified", unverified),
        ("leaked", leaked),
        ("sourceRetained", source),
        ("queuedJob", queued),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    state = payload["state"]
    if state not in _STATES:
        raise ValueError("state is unsupported")
    return phase, site, invalid, stale, unverified, leaked, state, source, queued


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P067-07 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
