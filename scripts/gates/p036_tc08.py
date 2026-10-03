"""TC-P036-08 throughput stage conflation.

Intervention: Supply fast acquisition-only evidence but a slower or failing
saved-source experiment.
Expected: Report separate stage rates and qualify only the successfully retained
complete path. This host gate never uses decision qualified or allowed.
Negative: Advertising discarded-frame acquisition speed as saved RAW recording
performance must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P036-08"
INTERVENTION = (
    "Supply fast acquisition-only evidence but a slower or failing saved-source experiment."
)
EXPECTED = (
    "Report separate stage rates and qualify only the successfully retained complete path."
)
NEGATIVE = (
    "Advertising discarded-frame acquisition speed as saved RAW recording performance must fail."
)

_DURATIONS = ("baseline", "increasing")
_AUDIO = ("off", "on")
_THERMAL = ("nominal", "elevated")
_UINT = re.compile(r"[1-9][0-9]*")
_PAYLOAD_KEYS = (
    "acquisitionRate",
    "savedRate",
    "savedComplete",
    "savedRetained",
    "framesDiscarded",
    "advertiseAcquisitionAsSaved",
    "duration",
    "storagePressure",
    "audioSelection",
    "thermalState",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "retained_path")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep acquisition and saved rates apart. Never certify the discard rate."""
    fields = _payload(payload)
    preserved = [
        f"acquisition:{fields['acquisitionRate']}",
        f"saved:{fields['savedRate']}",
        f"duration:{fields['duration']}",
        f"storagePressure:{str(fields['storagePressure']).lower()}",
        f"audio:{fields['audioSelection']}",
        f"thermal:{fields['thermalState']}",
    ]
    rejected: list[str] = []
    questions = [
        "acquisition-only rate is not saved RAW recording performance",
        "not a physical qualification",
    ]
    saved_ok = (
        fields["savedRate"] != "failing"
        and fields["savedComplete"]
        and fields["savedRetained"]
    )
    if fields["advertiseAcquisitionAsSaved"]:
        decision = "rejected"
        rejected.append("acquisition-advertised-as-saved-raw")
        reasons = [
            NEGATIVE,
            EXPECTED,
            (
                f"acquisition {fields['acquisitionRate']} stayed separate from "
                f"saved {fields['savedRate']}"
            ),
            "retained_path was not granted to discarded frames",
        ]
    elif saved_ok:
        decision = "retained_path"
        reasons = [
            EXPECTED,
            (
                f"separate rates acquisition {fields['acquisitionRate']} "
                f"and saved {fields['savedRate']}"
            ),
            "only the retained complete saved path is reported",
            "retained_path is not a qualified or allowed physical recording",
        ]
    else:
        decision = "withheld"
        reasons = [
            EXPECTED,
            (
                f"separate rates acquisition {fields['acquisitionRate']} "
                f"and saved {fields['savedRate']}"
            ),
            "saved-source path was not a successfully retained complete path",
        ]
        if fields["savedRate"] == "failing":
            questions.append("saved-source experiment failing")
        if fields["storagePressure"]:
            questions.append("storage pressure")
        if fields["thermalState"] == "elevated":
            questions.append("thermal state elevated")
    if fields["duration"] == "increasing":
        reasons.append("increasing duration did not merge the stage rates")
    if fields["audioSelection"] == "on":
        reasons.append("audio selection did not merge the stage rates")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    acquisition = payload["acquisitionRate"]
    saved = payload["savedRate"]
    if not isinstance(acquisition, str) or _UINT.fullmatch(acquisition) is None:
        raise ValueError("acquisitionRate must be a canonical positive integer string")
    if saved != "failing" and (not isinstance(saved, str) or _UINT.fullmatch(saved) is None):
        raise ValueError("savedRate must be failing or a canonical positive integer string")
    if saved != "failing" and int(acquisition) <= int(saved):
        raise ValueError("acquisition-only evidence must be faster than saved-source")
    complete = payload["savedComplete"]
    retained = payload["savedRetained"]
    discarded = payload["framesDiscarded"]
    advertise = payload["advertiseAcquisitionAsSaved"]
    pressure = payload["storagePressure"]
    if (
        type(complete) is not bool
        or type(retained) is not bool
        or type(discarded) is not bool
        or type(advertise) is not bool
        or type(pressure) is not bool
    ):
        raise ValueError("flags must be bools")
    if discarded is not True:
        raise ValueError("acquisition-only evidence discards frames")
    if saved == "failing" and complete:
        raise ValueError("a failing saved-source experiment is not complete")
    duration = payload["duration"]
    audio = payload["audioSelection"]
    thermal = payload["thermalState"]
    if duration not in _DURATIONS:
        raise ValueError("duration must be baseline or increasing")
    if audio not in _AUDIO:
        raise ValueError("audioSelection must be off or on")
    if thermal not in _THERMAL:
        raise ValueError("thermalState must be nominal or elevated")
    return {
        "acquisitionRate": acquisition,
        "savedRate": saved,
        "savedComplete": complete,
        "savedRetained": retained,
        "framesDiscarded": discarded,
        "advertiseAcquisitionAsSaved": advertise,
        "duration": duration,
        "storagePressure": pressure,
        "audioSelection": audio,
        "thermalState": thermal,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("stage decision cannot be qualified or allowed")
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
