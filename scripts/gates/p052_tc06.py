"""TC-P052-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene
feature under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P052-06"
INTERVENTION = "Place a persistent sensor defect beside a real small moving bright feature."
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."

_SITES = ("frame", "saturated-boundary")
_PAYLOAD_KEYS = (
    "frameId",
    "site",
    "defectId",
    "highlightId",
    "defectCorrected",
    "highlightPreserved",
    "removeAllIsolated",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")


def evaluate(payload: dict) -> dict:
    """Correct a supported defect without erasing the real highlight."""
    frame, site, defect, highlight, corrected, preserved_flag, remove_all = _payload(payload)
    preserved = [
        f"frame:{frame}",
        f"site:{site}",
        f"defect:{defect}:corrected={str(corrected).lower()}",
        f"highlight:{highlight}:preserved={str(preserved_flag).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = ["defect and highlight identities both stay in the inventory"]
    if remove_all:
        decision = "rejected"
        rejected.append("remove-all-isolated-bright")
        if not preserved_flag:
            rejected.append("highlight-removed")
        reasons.append(NEGATIVE)
        questions.append("blanket bright-pixel removal rejected")
    elif corrected and preserved_flag:
        decision = "kept-highlight"
        reasons.append("supported defect corrected and the moving highlight kept")
        questions.append("kept-highlight is not a physical defect map")
    elif corrected and not preserved_flag:
        decision = "rejected"
        rejected.append("highlight-removed")
        reasons.append("the real highlight was not preserved")
    elif preserved_flag:
        decision = "withheld"
        rejected.append("defect-uncorrected")
        reasons.append("highlight kept but the supported defect was not corrected")
    else:
        decision = "rejected"
        rejected.append("defect-uncorrected")
        rejected.append("highlight-removed")
        reasons.append("neither the defect correction nor the highlight survived")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    tokens = []
    for name in ("frameId", "defectId", "highlightId"):
        value = payload[name]
        if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
            raise ValueError(f"{name} must be a token")
        tokens.append(value)
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    flags = []
    for name in ("defectCorrected", "highlightPreserved", "removeAllIsolated"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    if tokens[1] == tokens[2]:
        raise ValueError("defect and highlight identities must differ")
    return (tokens[0], site, tokens[1], tokens[2], *flags)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-06 must not yield qualified or allowed")
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
