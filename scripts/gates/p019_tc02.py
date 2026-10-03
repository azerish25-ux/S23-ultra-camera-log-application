"""TC-P019-02 result differs from request.

Valid capture results that disagree with the requested control, or that omit
confirmation metadata, stay on the observed value. Confirmed-control readiness
is withheld. Showing the request as a measured value is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P019-02"
INTERVENTION = (
    "Return valid capture results that disagree with the requested control target "
    "or omit confirmation metadata."
)
EXPECTED = (
    "Display actual observations and withhold confirmed-control readiness "
    "according to the declared policy."
)
NEGATIVE = "Showing requested settings as measured values must fail."
REPEAT = (
    "Repeat for ISO, shutter duration, white-balance lock, lens focus, "
    "and active physical route."
)
CONTROLS = (
    "iso",
    "shutter_duration",
    "white_balance_lock",
    "lens_focus",
    "active_physical_route",
)
_PAYLOAD_KEYS = (
    "control",
    "requested",
    "observed",
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
    """Keep the observation. Never present the request as the measurement."""
    control, requested, observed, show_requested = _payload(payload)
    observed_token = "omitted" if observed is None else observed
    preserved = [f"observed:{observed_token}", f"requested:{requested}", f"control:{control}"]
    reasons = [f"control {control}", f"requested {requested}", f"observed {observed_token}"]
    rejected: list[str] = []
    questions: list[str] = []

    if show_requested:
        decision = "rejected"
        rejected.append("requested-as-measured")
        rejected.append(control)
        reasons.append("requested settings were not measured values")
    elif observed is None or observed != requested:
        decision = "withheld"
        rejected.append("confirmed-control")
        reasons.append("display actual observations")
        reasons.append("confirmed-control readiness withheld")
        if observed is None:
            questions.append("confirmation metadata omitted")
        else:
            questions.append("observation disagrees with the requested target")
    else:
        decision = "observation_recorded"
        reasons.append("observation matches the request and is still not a qualified measurement")

    if f"observed:{observed_token}" not in preserved:
        raise ValueError("actual observation must be preserved")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P019-02 must not yield qualified or allowed")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str | None, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    control = payload["control"]
    if control not in CONTROLS:
        raise ValueError("control is not a P019 repeat")
    requested = payload["requested"]
    if not isinstance(requested, str) or not requested or requested != requested.strip():
        raise ValueError("requested must be a non-empty string")
    observed = payload["observed"]
    if observed is not None:
        if not isinstance(observed, str) or not observed or observed != observed.strip():
            raise ValueError("observed must be a non-empty string or null")
    show_requested = payload["showRequestedAsMeasured"]
    if type(show_requested) is not bool:
        raise ValueError("showRequestedAsMeasured must be a bool")
    return control, requested, observed, show_requested


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
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
