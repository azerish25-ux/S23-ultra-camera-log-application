"""TC-P022-02 result differs from request.

Return valid capture results that disagree with the requested control target
or omit confirmation metadata. Display actual observations and withhold
confirmed-control readiness. Showing requested settings as measured values
must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-02"
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
    "confirmationPresent",
    "displayRequestedAsMeasured",
    "cleanMasterHash",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_OMITTED = "observation-omitted"


def evaluate(payload: dict) -> dict:
    """Show the observation. Never publish the request as the measurement."""
    data = _payload(payload)
    observed = data["observed"]
    shown = observed if observed is not None else _OMITTED
    reasons = [f"control {data['control']}", f"requested {data['requested']}", f"observed {shown}"]
    rejected: list[str] = []
    questions: list[str] = []
    disagree = observed is None or observed != data["requested"]
    if data["displayRequestedAsMeasured"]:
        decision = "rejected"
        rejected.append("requested-shown-as-measured")
        reasons.append("requested settings must not be shown as measured values")
    elif disagree or not data["confirmationPresent"]:
        decision = "withheld"
        reasons.append("confirmed-control readiness withheld")
        if not data["confirmationPresent"]:
            questions.append("confirmation metadata omitted")
        if disagree:
            questions.append("confirmed-control readiness withheld")
    else:
        decision = "observed"
        reasons.append("observation matches the request and confirmation metadata is present")
    preserved = [shown, data["control"], data["cleanMasterHash"]]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    control = payload["control"]
    if control not in CONTROLS:
        raise ValueError("control is not a declared repeat")
    requested = _token(payload["requested"], "requested")
    observed = payload["observed"]
    if observed is not None:
        observed = _token(observed, "observed")
    confirmation = _bool(payload["confirmationPresent"], "confirmationPresent")
    displayed = _bool(payload["displayRequestedAsMeasured"], "displayRequestedAsMeasured")
    clean = _token(payload["cleanMasterHash"], "cleanMasterHash")
    return {
        "control": control,
        "requested": requested,
        "observed": observed,
        "confirmationPresent": confirmation,
        "displayRequestedAsMeasured": displayed,
        "cleanMasterHash": clean,
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
        raise ValueError("TC-P022-02 must not yield qualified or allowed")
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
