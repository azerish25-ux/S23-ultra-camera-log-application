"""TC-P057-08 consumer round-trip discrepancy.

Intervention: Decode or import the accepted file in an independent consumer
using the documented settings.
Expected: Match the declared numeric and visual reference within the stated
codec and transform tolerance.
Negative: Successful file opening alone must not count as interoperability.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P057-08"
INTERVENTION = (
    "Decode or import the accepted file in an independent consumer using the "
    "documented settings."
)
EXPECTED = (
    "Match the declared numeric and visual reference within the stated codec and "
    "transform tolerance."
)
NEGATIVE = "Successful file opening alone must not count as interoperability."

_RANGES = ("full", "video", "unspecified")
_SIDECARS = ("present", "absent")
_PAYLOAD_KEYS = (
    "consumer",
    "version",
    "rangeSetting",
    "sidecar",
    "numericDelta",
    "tolerance",
    "opened",
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
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Require a numeric match. Opening the file is not interoperability."""
    consumer, version, range_setting, sidecar, delta, tolerance, opened = _payload(payload)
    preserved = [
        f"consumer:{consumer}",
        f"version:{version}",
        f"range:{range_setting}",
        f"sidecar:{sidecar}",
        f"numeric-delta:{delta}",
        f"tolerance:{tolerance}",
        f"opened:{str(opened).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["host numeric match is not a physical consumer certification"]
    matched = Decimal(delta) <= Decimal(tolerance)
    settings_ok = range_setting in {"full", "video"} and sidecar == "present"
    if not opened:
        reasons.append("the file was not opened, so interoperability was not shown")
        return _result("withheld", reasons, [], preserved, questions)
    if matched and settings_ok:
        reasons.append(f"{consumer} {version} matched within the stated tolerance")
        questions.append("within tolerance is not cinema-camera equivalence")
        return _result("within_tolerance", reasons, [], preserved, questions)
    reasons.append(NEGATIVE)
    claims = ["file-open-is-not-interoperability"]
    if not matched:
        claims.append("numeric-delta")
        reasons.append("numeric delta exceeded the stated tolerance")
    if range_setting == "unspecified":
        claims.append("range-unspecified")
    if sidecar == "absent":
        claims.append("sidecar-absent")
    return _result("rejected", reasons, claims, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    consumer = payload["consumer"]
    version = payload["version"]
    if not isinstance(consumer, str) or _TOKEN.fullmatch(consumer) is None:
        raise ValueError("consumer must be a token")
    if not isinstance(version, str) or _TOKEN.fullmatch(version) is None:
        raise ValueError("version must be a token")
    range_setting = payload["rangeSetting"]
    sidecar = payload["sidecar"]
    if range_setting not in _RANGES:
        raise ValueError("rangeSetting is unknown")
    if sidecar not in _SIDECARS:
        raise ValueError("sidecar is unknown")
    delta = payload["numericDelta"]
    tolerance = payload["tolerance"]
    if not isinstance(delta, str) or _DECIMAL.fullmatch(delta) is None:
        raise ValueError("numericDelta must be a canonical decimal")
    if not isinstance(tolerance, str) or _DECIMAL.fullmatch(tolerance) is None:
        raise ValueError("tolerance must be a canonical decimal")
    if Decimal(tolerance) <= 0:
        raise ValueError("tolerance must be positive")
    opened = payload["opened"]
    if type(opened) is not bool:
        raise ValueError("opened must be a bool")
    return consumer, version, range_setting, sidecar, delta, tolerance, opened


def _result(decision, reasons, rejected, preserved, questions) -> dict:
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
