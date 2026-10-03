"""TC-P064-08 consumer round-trip discrepancy.

Intervention: Decode or import the accepted file in an independent consumer
using the documented settings.
Expected: Match the declared numeric and visual reference within the stated
codec and transform tolerance.
Negative: Successful file opening alone must not count as interoperability.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P064-08"
INTERVENTION = "Decode or import the accepted file in an independent consumer using the documented settings."
EXPECTED = (
    "Match the declared numeric and visual reference within the stated codec and transform tolerance."
)
NEGATIVE = "Successful file opening alone must not count as interoperability."
REPEAT = "Repeat with exact consumer versions, range settings, and sidecar availability."

_RANGES = ("full", "video", "unspecified")
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_PAYLOAD_KEYS = (
    "consumer",
    "consumerVersion",
    "rangeSetting",
    "sidecarAvailable",
    "fileOpened",
    "numericDelta",
    "visualDelta",
    "numericTolerance",
    "visualTolerance",
    "documentedSettings",
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
    """Require a tolerant match. Opening the file is not interoperability."""
    (
        consumer,
        version,
        range_setting,
        sidecar,
        opened,
        numeric,
        visual,
        numeric_tol,
        visual_tol,
        documented,
    ) = _payload(payload)
    within = Decimal(numeric) <= Decimal(numeric_tol) and Decimal(visual) <= Decimal(visual_tol)
    range_ok = range_setting in {"full", "video"}
    matched = opened and documented and range_ok and within
    preserved = [
        f"consumer:{consumer}",
        f"version:{version}",
        f"range:{range_setting}",
        f"sidecar:{_flag(sidecar)}",
        f"opened:{_flag(opened)}",
        f"numeric-delta:{numeric}",
        f"visual-delta:{visual}",
        f"numeric-tolerance:{numeric_tol}",
        f"visual-tolerance:{visual_tol}",
        f"documented-settings:{_flag(documented)}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT]
    if not sidecar:
        questions.append("sidecar unavailable")
    rejected: list[str] = []
    if opened and not matched:
        rejected.append("open-is-not-interoperable")
        reasons.append(NEGATIVE)
    if not within:
        rejected.append("outside-tolerance")
        reasons.append("numeric or visual delta is outside the stated tolerance")
    if opened and not documented:
        rejected.append("settings-not-documented")
        reasons.append("consumer settings were not the documented settings")
    if not range_ok:
        rejected.append("range-unspecified")
        reasons.append("range setting was not an exact full or video choice")
    if matched:
        decision = "within_tolerance"
        reasons.append("deltas are inside the stated codec and transform tolerance")
        questions.append("within tolerance is not physical interoperability or qualification")
    elif opened or not within or not range_ok:
        decision = "rejected"
        questions.append("file opening was not counted as interoperability")
    else:
        decision = "withheld"
        questions.append("file was not opened")
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical non-negative decimal")
    return value


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    consumer = payload["consumer"]
    version = payload["consumerVersion"]
    if not isinstance(consumer, str) or _TOKEN.fullmatch(consumer) is None:
        raise ValueError("consumer must be a token")
    if not isinstance(version, str) or _TOKEN.fullmatch(version) is None:
        raise ValueError("consumerVersion must be a token")
    range_setting = payload["rangeSetting"]
    if range_setting not in _RANGES:
        raise ValueError("rangeSetting is unsupported")
    sidecar = payload["sidecarAvailable"]
    opened = payload["fileOpened"]
    documented = payload["documentedSettings"]
    for name, value in (
        ("sidecarAvailable", sidecar),
        ("fileOpened", opened),
        ("documentedSettings", documented),
    ):
        if type(value) is not bool:
            raise ValueError(name + " must be a bool")
    numeric = _decimal(payload["numericDelta"], "numericDelta")
    visual = _decimal(payload["visualDelta"], "visualDelta")
    numeric_tol = _decimal(payload["numericTolerance"], "numericTolerance")
    visual_tol = _decimal(payload["visualTolerance"], "visualTolerance")
    return (
        consumer,
        version,
        range_setting,
        sidecar,
        opened,
        numeric,
        visual,
        numeric_tol,
        visual_tol,
        documented,
    )


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-08 must not yield qualified or allowed")
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
