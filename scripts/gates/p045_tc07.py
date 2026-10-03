"""TC-P045-07 unrecorded measurement conditions.

Intervention: Remove illuminant, exposure, target identity, or source revision
from calibration evidence.
Expected: Downgrade or reject the measurement claim while retaining the data
for exploratory research.
Negative: An attractive color result without experimental context must not
become the default measured profile.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P045-07"
INTERVENTION = (
    "Remove illuminant, exposure, target identity, or source revision from "
    "calibration evidence."
)
EXPECTED = (
    "Downgrade or reject the measurement claim while retaining the data for "
    "exploratory research."
)
NEGATIVE = (
    "An attractive color result without experimental context must not become "
    "the default measured profile."
)

_FIELDS = ("illuminant", "exposure", "target", "revision")
_KINDS = ("measured", "author_assertion", "manufacturer_metadata")
_PAYLOAD_KEYS = (
    "dataId",
    "missing",
    "sourceKind",
    "attractiveResult",
    "makeDefault",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")


def evaluate(payload: dict) -> dict:
    """Downgrade evidence that lacks measurement context. Do not install a default."""
    data_id, missing, kind, attractive, make_default = _payload(payload)
    preserved = [f"data:{data_id}", f"source:{kind}"]
    preserved.extend(f"missing:{field}" for field in missing)
    preserved.append("attractive:" + ("yes" if attractive else "no"))
    reasons = [EXPECTED, INTERVENTION]
    questions = ["retained data is exploratory unless the measurement context is complete"]
    rejected: list[str] = []
    context_gap = bool(missing) or kind != "measured"
    for field in missing:
        rejected.append(f"missing:{field}")
    if kind == "author_assertion":
        rejected.append("author-assertion")
    elif kind == "manufacturer_metadata":
        rejected.append("manufacturer-metadata")
    if attractive and context_gap:
        rejected.append("attractive-without-context")
        reasons.append(NEGATIVE)
    if make_default and context_gap:
        decision = "rejected"
        rejected.insert(0, "default-without-context")
        reasons.append(NEGATIVE)
        reasons.append("retained data was not installed as the default measured profile")
        questions.append("default measured profile was refused")
    elif context_gap:
        decision = "exploratory"
        reasons.append("measurement claim downgraded; data retained for exploratory research")
        questions.append("exploratory data is not the default measured profile")
    else:
        decision = "contextual"
        reasons.append("recorded conditions stay attached to the data")
        questions.append("contextual evidence is not a physical S23 qualification")
        if make_default:
            questions.append("this host gate does not install a default measured profile")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, list[str], str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    data_id = payload["dataId"]
    if not isinstance(data_id, str) or _TOKEN.fullmatch(data_id) is None:
        raise ValueError("dataId must be a token")
    missing = payload["missing"]
    if type(missing) is not list or any(item not in _FIELDS for item in missing):
        raise ValueError("missing must list known condition fields")
    if len(missing) != len(set(missing)):
        raise ValueError("missing fields must be unique")
    kind = payload["sourceKind"]
    if kind not in _KINDS:
        raise ValueError("sourceKind is unsupported")
    attractive = payload["attractiveResult"]
    make_default = payload["makeDefault"]
    if type(attractive) is not bool or type(make_default) is not bool:
        raise ValueError("attractiveResult and makeDefault must be bools")
    return data_id, list(missing), kind, attractive, make_default


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-07 must not yield qualified or allowed")
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
