"""TC-P063-08 consumer round-trip discrepancy.

An independent consumer matches the reference only inside the stated
tolerance, with settings applied, a recorded version, and a sidecar.
Opening the file alone is not interoperability. This host case does not
qualify a physical S23.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P063-08"
INTERVENTION = "Decode or import the accepted file in an independent consumer using the documented settings."
EXPECTED = (
    "Match the declared numeric and visual reference within the stated codec and transform tolerance."
)
NEGATIVE = "Successful file opening alone must not count as interoperability."
REPEAT = "Repeat with exact consumer versions, range settings, and sidecar availability."

_RANGES = ("video", "full")
_PAYLOAD_KEYS = (
    "consumerId",
    "version",
    "rangeSetting",
    "sidecarAvailable",
    "opened",
    "settingsApplied",
    "numericDelta",
    "tolerance",
    "visualMatch",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Compare a consumer round trip, and reject opening-alone as interoperability."""
    (
        consumer,
        version,
        range_setting,
        sidecar,
        opened,
        settings_applied,
        delta,
        tolerance,
        visual,
    ) = _payload(payload)
    preserved = [
        consumer,
        f"version:{version}",
        f"range:{range_setting}",
        f"sidecar:{'true' if sidecar else 'false'}",
        f"opened:{'true' if opened else 'false'}",
        f"delta:{delta}",
        f"tolerance:{tolerance}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    within = Decimal(delta) <= Decimal(tolerance) and visual
    if not settings_applied:
        decision = "rejected"
        rejected = ["open-is-not-interoperability"]
        reasons.append(NEGATIVE)
        questions.append("opened state was preserved and was not treated as a match")
    elif not opened:
        decision = "rejected"
        rejected = ["consumer-did-not-open"]
        reasons.append("the independent consumer did not open the file")
    elif not within:
        decision = "rejected"
        rejected = ["round-trip-discrepancy"]
        reasons.append(f"delta {delta} against tolerance {tolerance} is not a match")
        if not visual:
            reasons.append("visual reference did not match")
    elif version == "unmeasured" or not sidecar:
        decision = "withheld"
        rejected = []
        reasons.append("numeric agreement without a recorded version and sidecar is not interoperability")
        questions.append("repeat requires an exact version, a range setting, and sidecar availability")
    else:
        decision = "within_tolerance"
        rejected = []
        reasons.append(f"delta {delta} is within tolerance {tolerance} for version {version}")
        questions.append("within_tolerance is not qualification and not cinema-camera equivalence")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    consumer = payload["consumerId"]
    version = payload["version"]
    if not isinstance(consumer, str) or _TOKEN.fullmatch(consumer) is None:
        raise ValueError("consumerId must be a token")
    if not isinstance(version, str) or _TOKEN.fullmatch(version) is None:
        raise ValueError("version must be a token")
    range_setting = payload["rangeSetting"]
    if range_setting not in _RANGES:
        raise ValueError("rangeSetting must be video or full")
    sidecar = payload["sidecarAvailable"]
    opened = payload["opened"]
    settings_applied = payload["settingsApplied"]
    visual = payload["visualMatch"]
    for name, flag in (
        ("sidecarAvailable", sidecar),
        ("opened", opened),
        ("settingsApplied", settings_applied),
        ("visualMatch", visual),
    ):
        if type(flag) is not bool:
            raise ValueError(f"{name} must be a bool")
    delta = payload["numericDelta"]
    tolerance = payload["tolerance"]
    for name, value in (("numericDelta", delta), ("tolerance", tolerance)):
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(f"{name} must be a canonical decimal")
    if Decimal(tolerance) <= 0:
        raise ValueError("tolerance must be positive")
    return consumer, version, range_setting, sidecar, opened, settings_applied, delta, tolerance, visual


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-08 must not yield qualified or allowed")
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
