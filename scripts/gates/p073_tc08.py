"""TC-P073-08 clipped-source overclaim.

Intervention: Use a source with irreversibly clipped regions and apply a soft film shoulder.
Expected: Render the desired appearance while retaining the limitation that missing
source detail was not recovered.
Negative: Softer highlight appearance must not be reported as recovered sensor information.
"""

from __future__ import annotations


CASE_ID = "TC-P073-08"
INTERVENTION = "Use a source with irreversibly clipped regions and apply a soft film shoulder."
EXPECTED = "Render the desired appearance while retaining the limitation that missing source detail was not recovered."
NEGATIVE = "Softer highlight appearance must not be reported as recovered sensor information."
REPEAT = "Repeat with clipped individual channels and fully clipped white regions."

_SCOPES = ("channel", "white", "none")
_PAYLOAD_KEYS = (
    "clipScope",
    "softShoulder",
    "appearanceApplied",
    "reportsRecoveredDetail",
    "missingDetailRetained",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "appearance_with_limitation"}


def evaluate(payload: dict) -> dict:
    """Apply a soft shoulder without reporting clipped source detail as recovered."""
    scope, shoulder, appearance, recovered, retained = _payload(payload)
    preserved = [
        f"clip:{scope}",
        f"shoulder:{str(shoulder).lower()}",
        f"appearance:{str(appearance).lower()}",
        f"missing-detail:{str(retained).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {scope}"]
    rejected: list[str] = []
    if recovered:
        decision = "rejected"
        rejected.append("recovered-detail")
        reasons.append(NEGATIVE)
        reasons.append(f"clip scope {scope} stays a limitation and is not recovered sensor information")
    elif scope != "none" and not retained:
        decision = "rejected"
        rejected.append("limitation-dropped")
        reasons.append(f"missing source detail for {scope} clipping was dropped")
    elif scope != "none" and shoulder and appearance and retained:
        decision = "appearance_with_limitation"
        reasons.append(f"soft shoulder renders {scope} clipping while missing source detail stays unrecovered")
        questions.append("appearance with a retained limitation is not recovered sensor information")
    elif scope == "none":
        decision = "withheld"
        reasons.append("no clipped source region is present")
    else:
        decision = "withheld"
        reasons.append("soft shoulder or appearance was not applied")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    scope = payload["clipScope"]
    if scope not in _SCOPES:
        raise ValueError("clipScope is unsupported")
    flags = []
    for name in ("softShoulder", "appearanceApplied", "reportsRecoveredDetail", "missingDetailRetained"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return scope, flags[0], flags[1], flags[2], flags[3]


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-08 must not yield qualified or allowed")
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
