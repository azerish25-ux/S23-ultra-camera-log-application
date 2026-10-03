"""TC-P037-08 throughput stage conflation.

Acquisition-only and saved-source rates stay separate. A retained complete
saved path is a software label only. Advertising the discarded-frame
acquisition speed as saved RAW recording performance is rejected.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P037-08"
INTERVENTION = "Supply fast acquisition-only evidence but a slower or failing saved-source experiment."
EXPECTED = "Report separate stage rates and qualify only the successfully retained complete path."
NEGATIVE = "Advertising discarded-frame acquisition speed as saved RAW recording performance must fail."

_REPEATS = ("increasing_duration", "storage_pressure", "audio_selection", "thermal_state")
_RATE = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")
_PAYLOAD_KEYS = (
    "acquisitionOnlyFps",
    "savedSourceFps",
    "savedRetained",
    "repeat",
    "advertiseAcquisitionAsSaved",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep acquisition-only speed distinct from saved RAW retention."""
    fields = _payload(payload)
    acq = fields["acquisitionOnlyFps"]
    saved = fields["savedSourceFps"]
    preserved = [f"acquisitionOnly:{acq}", f"savedSource:{saved}", f"repeat:{fields['repeat']}"]
    reasons = [
        EXPECTED,
        f"acquisition-only rate {acq}",
        f"saved-source rate {saved}",
        f"repeat {fields['repeat']}",
    ]
    if fields["advertiseAcquisitionAsSaved"]:
        reasons.append(NEGATIVE)
        reasons.append("acquisition-only rate was not reported as saved RAW performance")
        return _result(
            "rejected",
            reasons,
            ["acquisition-advertised-as-saved-raw"],
            preserved,
            ["discarded-frame acquisition speed is not a recording rate"],
        )
    if fields["savedRetained"]:
        reasons.append("saved-source path retained its own rate")
        reasons.append("retained_complete_path is not physical qualification")
        return _result("retained_complete_path", reasons, [], preserved, [])
    reasons.append("saved-source path was not retained")
    return _result(
        "stages_separated",
        reasons,
        [],
        preserved,
        ["saved-source path was not retained; acquisition-only rate is not saved RAW performance"],
    )


def _rate(value: object, label: str, allow_zero: bool) -> str:
    if not isinstance(value, str) or _RATE.fullmatch(value) is None:
        raise ValueError(label + " must be a decimal rate string")
    if value.endswith("."):
        raise ValueError(label + " must be a decimal rate string")
    if not allow_zero and (value == "0" or value.startswith("0.")):
        raise ValueError(label + " must be positive")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    acquired = _rate(payload["acquisitionOnlyFps"], "acquisitionOnlyFps", False)
    saved = _rate(payload["savedSourceFps"], "savedSourceFps", True)
    retained = payload["savedRetained"]
    if type(retained) is not bool:
        raise ValueError("savedRetained must be a bool")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is not a TC-P037-08 repeat")
    advertise = payload["advertiseAcquisitionAsSaved"]
    if type(advertise) is not bool:
        raise ValueError("advertiseAcquisitionAsSaved must be a bool")
    if retained and saved in {"0", "0.0"}:
        raise ValueError("a retained saved path needs a positive saved-source rate")
    return {
        "acquisitionOnlyFps": acquired,
        "savedSourceFps": saved,
        "savedRetained": retained,
        "repeat": repeat,
        "advertiseAcquisitionAsSaved": advertise,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P037-08 must not yield qualified or allowed")
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
