"""TC-P059-08 consumer round-trip discrepancy.

Intervention: Decode or import the accepted file in an independent consumer
using the documented settings.
Expected: Match the declared numeric and visual reference within the stated
codec and transform tolerance.
Negative: Successful file opening alone must not count as interoperability.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P059-08"
INTERVENTION = (
    "Decode or import the accepted file in an independent consumer using the documented settings."
)
EXPECTED = (
    "Match the declared numeric and visual reference within the stated codec and transform tolerance."
)
NEGATIVE = "Successful file opening alone must not count as interoperability."

_RANGES = ("full", "video", "missing")
_SIDECARS = ("present", "absent")
_REPEATS = ("none", "consumer-version", "range-setting", "sidecar")
_PAYLOAD_KEYS = (
    "consumer",
    "consumerVersion",
    "opened",
    "openOnly",
    "numericError",
    "visualError",
    "tolerance",
    "rangeSetting",
    "sidecar",
    "repeat",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "within_tolerance")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_NUMBER = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Compare consumer errors. Opening the file is not interoperability."""
    (
        consumer,
        version,
        opened,
        open_only,
        numeric,
        visual,
        tolerance,
        range_setting,
        sidecar,
        repeat,
    ) = _payload(payload)
    preserved = [
        "consumer:" + consumer,
        "version:" + version,
        "opened:" + ("true" if opened else "false"),
        "numeric-error:" + numeric,
        "visual-error:" + visual,
        "tolerance:" + tolerance,
        "range:" + range_setting,
        "sidecar:" + sidecar,
        "repeat:" + repeat,
    ]
    within = Decimal(numeric) <= Decimal(tolerance) and Decimal(visual) <= Decimal(tolerance)
    reasons = [EXPECTED, INTERVENTION]
    if open_only:
        reasons.append(NEGATIVE)
        reasons.append("file open was not counted as interoperability")
        return _result(
            "rejected",
            reasons,
            ["open-is-not-interoperable"],
            preserved,
            ["opening the file is not a round trip"],
        )
    if not within:
        reasons.append("numeric or visual error exceeds the stated tolerance")
        return _result(
            "rejected",
            reasons,
            ["round-trip-mismatch"],
            preserved,
            ["consumer discrepancy remains"],
        )
    if range_setting == "missing" or sidecar == "absent":
        reasons.append("documented range or sidecar is incomplete")
        return _result(
            "withheld",
            reasons,
            ["incomplete-consumer-settings"],
            preserved,
            ["tolerance match without documented settings is not interoperability"],
        )
    reasons.append("numeric and visual errors are inside the stated tolerance")
    reasons.append("tolerance match is not physical interoperability qualification")
    return _result(
        "within_tolerance",
        reasons,
        [],
        preserved,
        ["host tolerance match is not a device round trip"],
    )


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
    opened = payload["opened"]
    open_only = payload["openOnly"]
    if type(opened) is not bool or type(open_only) is not bool:
        raise ValueError("opened and openOnly must be bools")
    numeric = _number(payload["numericError"], "numericError")
    visual = _number(payload["visualError"], "visualError")
    tolerance = _number(payload["tolerance"], "tolerance")
    range_setting = payload["rangeSetting"]
    if range_setting not in _RANGES:
        raise ValueError("rangeSetting is unsupported")
    sidecar = payload["sidecar"]
    if sidecar not in _SIDECARS:
        raise ValueError("sidecar must be present or absent")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is unsupported")
    return (
        consumer,
        version,
        opened,
        open_only,
        numeric,
        visual,
        tolerance,
        range_setting,
        sidecar,
        repeat,
    )


def _number(value: object, label: str) -> str:
    if not isinstance(value, str) or _NUMBER.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical decimal string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-08 must not yield qualified or allowed")
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
