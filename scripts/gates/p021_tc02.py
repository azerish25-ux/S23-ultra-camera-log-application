"""TC-P021-02 result differs from request.

Valid capture results that disagree with the requested control, or that omit
confirmation, are displayed as observations. Confirmed-control readiness is
withheld. Showing the requested setting as a measured value is rejected.

Baseline focus inventory stays in preservedResults. This host module does not
touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P021-02"
INTERVENTION = (
    "Return valid capture results that disagree with the requested control "
    "target or omit confirmation metadata."
)
EXPECTED = (
    "Display actual observations and withhold confirmed-control readiness "
    "according to the declared policy."
)
NEGATIVE = "Showing requested settings as measured values must fail."
REPEATS = (
    "iso",
    "shutter_duration",
    "white_balance_lock",
    "lens_focus",
    "active_physical_route",
)
FOCUS_INVENTORY = (
    "physical.namespace:physical.lens",
    "physical.unit:metres",
    "physical.subject:nearby_foreground",
    "physical.distance:unknown",
    "virtual.namespace:virtual.development",
    "virtual.unit:relative_depth",
    "virtual.subject:face",
    "virtual.relativeDepth:0.62",
)
_PAYLOAD_KEYS = {"control", "requested", "observed", "presentRequestedAsMeasured"}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_WITHHELD = "confirmed-control readiness withheld"


def evaluate(payload: dict) -> dict:
    """Show observations. Never promote a request into a measurement."""
    control, requested, observed, present_requested = _payload(payload)
    preserved = list(FOCUS_INVENTORY)
    preserved.append("requested:" + control + ":" + requested)
    if observed is None:
        preserved.append("observed:" + control + ":omitted")
    else:
        preserved.append("observed:" + control + ":" + observed)
    reasons = [EXPECTED, "repeat control " + control]
    questions: list[str] = []
    rejected: list[str] = []

    if present_requested:
        decision = "rejected"
        rejected.append("requested-as-measured")
        reasons.append(NEGATIVE)
        reasons.append("requested " + requested + " was not stored as a measured value")
        if any(item.startswith("measured:") for item in preserved):
            raise ValueError("requested value must not be stored as measured")
    elif observed is None or observed != requested:
        decision = "withheld"
        questions.append(_WITHHELD)
        if observed is None:
            reasons.append("confirmation metadata omitted for " + control)
        else:
            reasons.append(
                "observed " + observed + " disagrees with requested " + requested
            )
        reasons.append("actual observation displayed; confirmed-control readiness withheld")
    else:
        decision = "control_confirmed"
        preserved.append("measured:" + control + ":" + observed)
        reasons.append("observed " + observed + " matches the request for " + control)

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P021-02 must not decide qualified or allowed")
    if present_requested and decision in {"qualified", "allowed", "control_confirmed"}:
        raise ValueError("presenting the request as measured must fail")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    control = payload["control"]
    if control not in REPEATS:
        raise ValueError("control is not a TC-P021-02 repeat")
    requested = _text(payload["requested"], "requested")
    observed = payload["observed"]
    if observed is not None:
        observed = _text(observed, "observed")
    return (
        control,
        requested,
        observed,
        _bool(payload["presentRequestedAsMeasured"], "presentRequestedAsMeasured"),
    )


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(name + " must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(name + " must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("decision must not be qualified or allowed")
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
