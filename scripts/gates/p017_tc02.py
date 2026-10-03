"""TC-P017-02 result differs from request.

Valid capture results that disagree with the requested target, or that omit
confirmation metadata, stay on the observed value. Confirmed-control readiness
is withheld. Showing the request as if it were measured is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-02"
INTERVENTION = (
    "Return valid capture results that disagree with the requested control target "
    "or omit confirmation metadata."
)
EXPECTED = (
    "Display actual observations and withhold confirmed-control readiness "
    "according to the declared policy."
)
NEGATIVE = "Showing requested settings as measured values must fail."
CONTROLS = (
    "iso",
    "shutter_duration",
    "white_balance_lock",
    "lens_focus",
    "active_physical_route",
)
_OMITTED = "confirmation-omitted"
_PAYLOAD_KEYS = (
    "control",
    "requested",
    "observed",
    "confirmationPresent",
    "showRequestedAsMeasured",
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
    """Preserve the observation. Requested-as-measured is rejected."""
    control, requested, observed, confirmation, show_requested = _payload(payload)
    reasons = [
        f"control {control}",
        INTERVENTION,
        EXPECTED,
        "display actual observations",
    ]
    rejected: list[str] = []
    open_questions: list[str] = []
    disagree = observed is None or observed != requested or not confirmation
    if show_requested:
        rejected.append("requested-as-measured")
        reasons.append(NEGATIVE)
        decision = "rejected"
    elif disagree:
        decision = "withheld"
        reasons.append("confirmed-control readiness withheld")
        open_questions.append("confirmed-control readiness withheld")
    else:
        decision = "observed"
        reasons.append("observation matches the requested target with confirmation metadata")
        reasons.append("a matching observation is not physical qualification")
    preserved = [_OMITTED] if observed is None else [observed]
    if observed is not None and observed != requested and requested in preserved:
        raise ValueError("requested target must not replace the observation")
    if observed is None and requested in preserved:
        raise ValueError("omitted confirmation must not preserve the request as measured")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> tuple[str, str, str | None, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    control = payload["control"]
    if control not in CONTROLS:
        raise ValueError("control is not a TC-P017-02 repeat")
    requested = _text(payload["requested"], "requested")
    observed = payload["observed"]
    if observed is not None:
        observed = _text(observed, "observed")
    confirmation = _bool(payload["confirmationPresent"], "confirmationPresent")
    show_requested = _bool(payload["showRequestedAsMeasured"], "showRequestedAsMeasured")
    if confirmation and observed is None:
        raise ValueError("confirmationPresent requires an observation")
    return control, requested, observed, confirmation, show_requested


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P017-02 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
