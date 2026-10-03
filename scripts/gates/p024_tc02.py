"""TC-P024-02 result differs from request.

Valid capture results that disagree with the requested control, or that omit
confirmation metadata, stay on the observed side. Confirmed-control readiness
is withheld. Presenting the request as the measured value fails.
"""

from __future__ import annotations

CASE_ID = "TC-P024-02"
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
_PAYLOAD_KEYS = (
    "control",
    "requested",
    "observed",
    "presentedAs",
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
    """Withhold confirmed control when observation disagrees or is omitted."""
    fields = _payload(payload)
    observed = fields["observed"]
    observation = observed if observed is not None else "confirmation-omitted"
    preserved = [
        f"control:{fields['control']}",
        f"requested:{fields['requested']}",
        observation,
    ]
    reasons = [
        f"control {fields['control']} presented as {fields['presentedAs']}",
        INTERVENTION,
    ]
    rejected: list[str] = []
    if fields["presentedAs"] == "requested":
        decision = "rejected"
        rejected.append("requested-shown-as-measured")
        reasons.append(NEGATIVE)
        reasons.append("requested settings are not measured values")
    else:
        decision = "withheld"
        reasons.append(EXPECTED)
        reasons.append("confirmed-control readiness withheld; observation kept")
    open_questions = ["confirmed-control readiness withheld"]
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    control = payload["control"]
    if control not in CONTROLS:
        raise ValueError("control is not a TC-P024-02 repeat")
    requested = _label(payload["requested"], "requested")
    observed = payload["observed"]
    if observed is not None:
        observed = _label(observed, "observed")
        if observed == requested:
            raise ValueError("intervention requires disagreement or omitted confirmation")
    presented = payload["presentedAs"]
    if presented not in {"observed", "requested"}:
        raise ValueError("presentedAs must be observed or requested")
    return {
        "control": control,
        "requested": requested,
        "observed": observed,
        "presentedAs": presented,
    }


def _label(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\n" in value:
        raise ValueError(f"{name} must be a non-empty single-line string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P024-02 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
