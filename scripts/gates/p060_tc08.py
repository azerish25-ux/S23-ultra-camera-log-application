"""TC-P060-08 consumer round-trip discrepancy.

Intervention: Decode or import the accepted file in an independent consumer
using the documented settings.
Expected: Match the declared numeric and visual reference within the stated
codec and transform tolerance.
Negative: Successful file opening alone must not count as interoperability.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P060-08"
INTERVENTION = "Decode or import the accepted file in an independent consumer using the documented settings."
EXPECTED = "Match the declared numeric and visual reference within the stated codec and transform tolerance."
NEGATIVE = "Successful file opening alone must not count as interoperability."
REPEAT = "Repeat with exact consumer versions, range settings, and sidecar availability."

_TOKEN = re.compile(r"^[a-z0-9.-]{1,40}$")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_RANGES = ("limited", "full", "unspecified")
_EXPECTED = ("limited", "full")
_SIDECARS = ("present", "absent", "ignored")
_PAYLOAD_KEYS = (
    "consumer",
    "consumerVersion",
    "fileOpened",
    "rangeSetting",
    "expectedRange",
    "sidecar",
    "numericDelta",
    "tolerance",
    "visualDelta",
    "visualTolerance",
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
    """Match numeric and visual deltas. Opening the file is not interoperability."""
    fields = _payload(payload)
    numeric_ok = fields["numericDelta"] <= fields["tolerance"]
    visual_ok = fields["visualDelta"] <= fields["visualTolerance"]
    range_ok = fields["rangeSetting"] == fields["expectedRange"]
    sidecar_ok = fields["sidecar"] == "present"
    preserved = [
        f"consumer:{fields['consumer']}",
        f"version:{fields['consumerVersion']}",
        f"opened:{'yes' if fields['fileOpened'] else 'no'}",
        f"range:{fields['rangeSetting']}|{fields['expectedRange']}",
        f"sidecar:{fields['sidecar']}",
        f"numeric:{fields['numericText']}/{fields['toleranceText']}",
        f"visual:{fields['visualText']}/{fields['visualToleranceText']}",
    ]
    reasons = [
        EXPECTED,
        INTERVENTION,
        f"consumer {fields['consumer']} {fields['consumerVersion']}",
    ]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    matched = numeric_ok and visual_ok and range_ok and sidecar_ok
    if not fields["fileOpened"]:
        decision = "withheld"
        reasons.append("the file was not opened, so no round trip was claimed")
        questions.append("opening was not treated as success")
    elif not matched:
        decision = "rejected"
        rejected.append("file-open-is-not-interoperability")
        reasons.append(NEGATIVE)
        if not numeric_ok or not visual_ok:
            rejected.append("outside-tolerance")
        if not range_ok:
            rejected.append("range-setting")
        if not sidecar_ok:
            rejected.append("sidecar-unavailable")
    else:
        decision = "matched"
        reasons.append("numeric and visual deltas are inside the stated tolerance")
        reasons.append(NEGATIVE)
        questions.append("file opening was not the matching evidence")
    return _result(decision, reasons, rejected, preserved, questions)


def _decimal(value: object, name: str) -> tuple[Decimal, str]:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical non-negative decimal")
    return Decimal(value), value


def _payload(payload: object) -> dict:
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
    opened = payload["fileOpened"]
    if type(opened) is not bool:
        raise ValueError("fileOpened must be a bool")
    range_setting = payload["rangeSetting"]
    expected = payload["expectedRange"]
    sidecar = payload["sidecar"]
    if range_setting not in _RANGES:
        raise ValueError("rangeSetting is unsupported")
    if expected not in _EXPECTED:
        raise ValueError("expectedRange is unsupported")
    if sidecar not in _SIDECARS:
        raise ValueError("sidecar is unsupported")
    numeric, numeric_text = _decimal(payload["numericDelta"], "numericDelta")
    tolerance, tolerance_text = _decimal(payload["tolerance"], "tolerance")
    visual, visual_text = _decimal(payload["visualDelta"], "visualDelta")
    visual_tolerance, visual_tolerance_text = _decimal(payload["visualTolerance"], "visualTolerance")
    return {
        "consumer": consumer,
        "consumerVersion": version,
        "fileOpened": opened,
        "rangeSetting": range_setting,
        "expectedRange": expected,
        "sidecar": sidecar,
        "numericDelta": numeric,
        "numericText": numeric_text,
        "tolerance": tolerance,
        "toleranceText": tolerance_text,
        "visualDelta": visual,
        "visualText": visual_text,
        "visualTolerance": visual_tolerance,
        "visualToleranceText": visual_tolerance_text,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-08 must not yield qualified or allowed")
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
