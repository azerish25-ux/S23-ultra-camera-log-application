"""TC-P049-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene
feature under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P049-06"
INTERVENTION = (
    "Place a persistent sensor defect beside a real small moving bright feature."
)
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the "
    "declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."

_SITES = ("interior", "saturated-boundary")
_PAYLOAD_KEYS = (
    "frameCount",
    "defectPersistent",
    "realHighlight",
    "site",
    "removeEveryIsolatedBright",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "defect_only", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Correct only a supported defect. Do not delete every isolated bright pixel."""
    frames, defect, highlight, site, remove_all = _payload(payload)
    preserved = [
        f"frames:{frames}",
        f"site:{site}",
        "real-highlight:preserved" if highlight else "real-highlight:absent",
        "defect:supported" if defect else "defect:absent",
    ]
    reasons = [EXPECTED]
    if remove_all:
        decision = "rejected"
        rejected = ["remove-every-isolated-bright"]
        reasons.append(NEGATIVE)
        questions = ["real highlight was not removed with isolated pixels"]
    elif defect and highlight:
        decision = "defect_only"
        rejected = []
        reasons.append("only the supported defect is corrected")
        questions = ["real moving highlight retained"]
    else:
        decision = "withheld"
        rejected = []
        reasons.append("supported defect and real feature were not both present")
        questions = ["no deletion of isolated bright pixels"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[int, bool, bool, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    frames = payload["frameCount"]
    if type(frames) is not int or not 1 <= frames <= 16:
        raise ValueError("frameCount must be an int from 1 to 16")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unknown")
    flags = []
    for name in ("defectPersistent", "realHighlight", "removeEveryIsolatedBright"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
        flags.append(payload[name])
    return frames, flags[0], flags[1], site, flags[2]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
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
