"""TC-P058-08 consumer round-trip discrepancy.

Intervention: Decode or import the accepted file in an independent consumer
using the documented settings.
Expected: Match the declared numeric and visual reference within the stated
codec and transform tolerance.
Negative: Successful file opening alone must not count as interoperability.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P058-08"
INTERVENTION = "Decode or import the accepted file in an independent consumer using the documented settings."
EXPECTED = "Match the declared numeric and visual reference within the stated codec and transform tolerance."
NEGATIVE = "Successful file opening alone must not count as interoperability."

_RANGES = ("full", "video")
_PAYLOAD_KEYS = (
    "consumerVersion",
    "documentedRange",
    "consumerRange",
    "sidecarAvailable",
    "fileOpened",
    "openedOnly",
    "numericDelta",
    "visualDelta",
    "numericTolerance",
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
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Require numeric and visual tolerance. Opening the file is not enough."""
    (
        version,
        documented,
        consumer,
        sidecar,
        opened,
        opened_only,
        numeric_delta,
        visual_delta,
        numeric_tol,
        visual_tol,
    ) = _payload(payload)
    preserved = [
        f"consumer:{version}",
        f"documented-range:{documented}",
        f"consumer-range:{consumer}",
        "sidecar:" + ("present" if sidecar else "absent"),
        "opened:" + ("true" if opened else "false"),
        f"numeric:{numeric_delta}/{numeric_tol}",
        f"visual:{visual_delta}/{visual_tol}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"consumer {version} is a host comparison, not a device proof"]
    if opened_only:
        decision = "rejected"
        rejected.append("open-is-not-interop")
        reasons.append(NEGATIVE)
        questions.append("file opening was not counted as interoperability")
        return _result(decision, reasons, rejected, preserved, questions)
    if Decimal(numeric_delta) > Decimal(numeric_tol) or Decimal(visual_delta) > Decimal(visual_tol):
        rejected.append("out-of-tolerance")
    if consumer != documented:
        rejected.append("range-setting")
    if not sidecar:
        rejected.append("sidecar-unavailable")
    if not opened:
        rejected.append("file-not-opened")
    if rejected:
        decision = "rejected"
        reasons.append("round trip missed the stated tolerance or settings")
    else:
        decision = "within_tolerance"
        reasons.append("numeric and visual deltas are inside the stated tolerance")
        reasons.append("opening the file was not the interoperability certificate")
        questions.append("tolerance match is not physical S23 qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    version = payload["consumerVersion"]
    if not isinstance(version, str) or _TOKEN.fullmatch(version) is None:
        raise ValueError("consumerVersion must be a token")
    documented = payload["documentedRange"]
    consumer = payload["consumerRange"]
    if documented not in _RANGES or consumer not in _RANGES:
        raise ValueError("range must be full or video")
    sidecar = payload["sidecarAvailable"]
    opened = payload["fileOpened"]
    opened_only = payload["openedOnly"]
    for name, value in (
        ("sidecarAvailable", sidecar),
        ("fileOpened", opened),
        ("openedOnly", opened_only),
    ):
        if type(value) is not bool:
            raise ValueError(name + " must be a bool")
    numbers = []
    for name in ("numericDelta", "visualDelta", "numericTolerance", "visualTolerance"):
        value = payload[name]
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(name + " must be a canonical decimal")
        numbers.append(value)
    return (version, documented, consumer, sidecar, opened, opened_only, *numbers)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P058-08 must not yield qualified or allowed")
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
