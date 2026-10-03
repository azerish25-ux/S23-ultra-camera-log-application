"""TC-P061-08 consumer round-trip discrepancy.

Intervention: Decode or import the accepted file in an independent consumer
using the documented settings.
Expected: Match the declared numeric and visual reference within the stated
codec and transform tolerance.
Negative: Successful file opening alone must not count as interoperability.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P061-08"
INTERVENTION = (
    "Decode or import the accepted file in an independent consumer using the documented settings."
)
EXPECTED = (
    "Match the declared numeric and visual reference within the stated codec and transform tolerance."
)
NEGATIVE = "Successful file opening alone must not count as interoperability."
REPEAT = "Repeat with exact consumer versions, range settings, and sidecar availability."

_RANGES = ("full", "video", "mismatched")
_SIDECARS = ("present", "absent")
_PAYLOAD_KEYS = (
    "consumerVersion",
    "rangeSetting",
    "expectedRange",
    "sidecar",
    "numericDelta",
    "tolerance",
    "visualMatch",
    "fileOpened",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_VERSION = re.compile(r"^[A-Za-z0-9._-]+$")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Require numeric and visual agreement. Opening the file is not enough."""
    version, range_setting, expected_range, sidecar, delta, tolerance, visual, opened = _payload(
        payload
    )
    preserved = [
        f"consumer:{version}",
        f"range:{range_setting}",
        f"expected-range:{expected_range}",
        f"sidecar:{sidecar}",
        f"delta:{delta}",
        f"tolerance:{tolerance}",
        f"opened:{str(opened).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    questions = ["host fixture is not a consumer interoperability certificate"]
    numeric_ok = Decimal(delta) <= Decimal(tolerance)
    range_ok = range_setting == expected_range and range_setting != "mismatched"
    sidecar_ok = sidecar == "present"
    within = opened and numeric_ok and visual and range_ok and sidecar_ok
    if within:
        decision = "within_tolerance"
        rejected: list[str] = []
        reasons.append("numeric and visual reference matched inside the stated tolerance")
        questions.append("within_tolerance is not physical file interoperability")
        return _result(decision, reasons, rejected, preserved, questions)
    rejected = []
    if opened:
        rejected.append("open-is-not-interoperability")
        reasons.append(NEGATIVE)
    else:
        rejected.append("file-not-opened")
        reasons.append("the independent consumer did not open the file")
    if not numeric_ok:
        rejected.append("numeric-discrepancy")
        reasons.append("numeric delta is outside the stated tolerance")
    if not visual:
        rejected.append("visual-discrepancy")
        reasons.append("visual reference did not match")
    if not range_ok:
        rejected.append("range-setting")
        reasons.append("consumer range setting does not match the documented range")
    if not sidecar_ok:
        rejected.append("sidecar-unavailable")
        reasons.append("documented sidecar was not available")
    return _result("rejected", reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    version = payload["consumerVersion"]
    if not isinstance(version, str) or _VERSION.fullmatch(version) is None:
        raise ValueError("consumerVersion must be a token")
    range_setting = payload["rangeSetting"]
    if range_setting not in _RANGES:
        raise ValueError("rangeSetting is unsupported")
    expected_range = payload["expectedRange"]
    if expected_range not in {"full", "video"}:
        raise ValueError("expectedRange is unsupported")
    sidecar = payload["sidecar"]
    if sidecar not in _SIDECARS:
        raise ValueError("sidecar is unsupported")
    delta = _decimal(payload["numericDelta"], "numericDelta")
    tolerance = _decimal(payload["tolerance"], "tolerance")
    if Decimal(tolerance) <= 0:
        raise ValueError("tolerance must be positive")
    visual = payload["visualMatch"]
    if type(visual) is not bool:
        raise ValueError("visualMatch must be a bool")
    opened = payload["fileOpened"]
    if type(opened) is not bool:
        raise ValueError("fileOpened must be a bool")
    return version, range_setting, expected_range, sidecar, delta, tolerance, visual, opened


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical non-negative decimal")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-08 must not yield qualified or allowed")
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
