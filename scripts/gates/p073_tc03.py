"""TC-P073-03 nonmonotonic density fit.

Intervention: Introduce a spline overshoot or malformed point that reverses density
ordering locally.
Expected: Reject or constrain the fit according to the stock model's declared
behavior before release.
Negative: A smooth-looking curve that reverses an exposure wedge must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P073-03"
INTERVENTION = "Introduce a spline overshoot or malformed point that reverses density ordering locally."
EXPECTED = "Reject or constrain the fit according to the stock model’s declared behavior before release."
NEGATIVE = "A smooth-looking curve that reverses an exposure wedge must fail."
REPEAT = "Repeat near toe, midsection, shoulder, and interpolation endpoints."

_REGIONS = ("toe", "midsection", "shoulder", "endpoint")
_BEHAVIOR = ("monotonic", "unconstrained")
_PAYLOAD_KEYS = ("region", "smoothLooking", "reversesWedge", "declaredBehavior", "released")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "fit_constrained"}


def evaluate(payload: dict) -> dict:
    """Reject a reversed exposure wedge, including one that looks smooth."""
    region, smooth, reverses, declared, released = _payload(payload)
    preserved = [
        f"region:{region}",
        f"smooth:{str(smooth).lower()}",
        f"wedge-reversed:{str(reverses).lower()}",
        f"declared:{declared}",
        f"released:{str(released).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {region}"]
    rejected: list[str] = []
    if reverses:
        rejected.append("wedge-reversal")
        reasons.append(NEGATIVE)
        reasons.append(f"{region} reversal fails before release")
        if smooth:
            reasons.append("smooth appearance does not excuse a reversed exposure wedge")
        if released:
            rejected.append("released-before-constraint")
            reasons.append("a reversed fit was marked released")
        decision = "rejected"
    elif declared == "monotonic":
        decision = "fit_constrained"
        reasons.append(f"{region} fit is constrained to the declared monotonic behavior")
        if released:
            questions.append("a constrained fit is not a qualified stock measurement")
        else:
            questions.append("constraint is recorded before release")
    elif released:
        decision = "rejected"
        rejected.append("unconstrained-release")
        reasons.append(f"unconstrained {region} fit cannot be released")
    else:
        decision = "withheld"
        reasons.append(f"unconstrained {region} fit is withheld before release")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    region = payload["region"]
    if region not in _REGIONS:
        raise ValueError("region is unsupported")
    declared = payload["declaredBehavior"]
    if declared not in _BEHAVIOR:
        raise ValueError("declaredBehavior is unsupported")
    smooth = payload["smoothLooking"]
    reverses = payload["reversesWedge"]
    released = payload["released"]
    for name, value in (
        ("smoothLooking", smooth),
        ("reversesWedge", reverses),
        ("released", released),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    return region, smooth, reverses, declared, released


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-03 must not yield qualified or allowed")
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
