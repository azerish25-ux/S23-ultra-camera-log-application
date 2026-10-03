"""TC-P018-01 late callback generation.

A successful callback from a previous camera or recording generation does not
mutate the current owner. Only resources that generation still owns are
released. Resurrecting recording or attaching an obsolete surface is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P018-01"
INTERVENTION = (
    "Deliver a successful callback from a previous camera or recording generation "
    "after the current owner has changed."
)
EXPECTED = (
    "Ignore stale state mutation and release only resources owned by the stale operation."
)
NEGATIVE = (
    "A delayed callback that resurrects recording or attaches an obsolete surface must fail."
)
REPEAT = (
    "Repeat before first sample, during stopping, after Activity recreation, "
    "and after camera reopen."
)
MOMENTS = (
    "before_first_sample",
    "during_stopping",
    "after_activity_recreation",
    "after_camera_reopen",
)
MOMENT_STATE = {
    "before_first_sample": "starting",
    "during_stopping": "stopping",
    "after_activity_recreation": "preview",
    "after_camera_reopen": "opening",
}
CALLBACK_TYPES = ("first_video_sample", "surface_attach", "audio_format", "success")
_PAYLOAD_KEYS = (
    "moment",
    "currentGeneration",
    "currentOwner",
    "recording",
    "attachedSurface",
    "currentResources",
    "callbackGeneration",
    "callbackOwner",
    "callbackType",
    "resurrectRecording",
    "attachObsoleteSurface",
    "staleResources",
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
    """Ignore a stale generation. Negative resurrection or surface attach is rejected."""
    fields = _payload(payload)
    reasons = [
        f"moment {fields['moment']} stays {fields['state']}",
        f"callback {fields['callbackType']} from generation {fields['callbackGeneration']}",
    ]
    rejected: list[str] = []
    released: list[str] = []
    stale = (
        fields["callbackGeneration"] != fields["currentGeneration"]
        or fields["callbackOwner"] != fields["currentOwner"]
    )
    if stale:
        released = list(fields["staleResources"])
        reasons.append(
            "stale callback ignored; released only resources owned by the stale operation"
        )
        if released:
            reasons.append("released " + ",".join(released))
        else:
            reasons.append("stale operation owned no releasable resources")
    else:
        reasons.append("callback generation matches the current owner")

    negative = fields["resurrectRecording"] or fields["attachObsoleteSurface"]
    if fields["resurrectRecording"]:
        rejected.append("resurrect-recording")
        reasons.append("delayed callback must not resurrect recording")
    if fields["attachObsoleteSurface"]:
        rejected.append("obsolete-surface")
        reasons.append("delayed callback must not attach an obsolete surface")

    if negative:
        decision = "rejected"
    elif stale:
        decision = "stale_ignored"
    else:
        decision = "not_stale"

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P018-01 must not yield qualified or allowed")
    preserved = _preserved(fields)
    for resource_id in fields["currentResources"]:
        if resource_id in released:
            raise ValueError("current owner resources must not be released")
    if fields["recording"] and "recording:true" not in preserved:
        raise ValueError("current recording evidence was dropped")
    return _result(decision, reasons, rejected, preserved, [])


def _preserved(fields: dict) -> list[str]:
    preserved = [f"resource:{item}" for item in fields["currentResources"]]
    preserved.append("surface:" + fields["attachedSurface"])
    preserved.append("recording:" + ("true" if fields["recording"] else "false"))
    preserved.append("state:" + fields["state"])
    preserved.append("owner:" + fields["currentOwner"])
    return preserved


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if tuple(payload) != _PAYLOAD_KEYS and set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    moment = payload["moment"]
    if moment not in MOMENTS:
        raise ValueError("moment is not a P018 late-callback repeat")
    current_generation = _generation(payload["currentGeneration"], "currentGeneration")
    callback_generation = _generation(payload["callbackGeneration"], "callbackGeneration")
    current_owner = _token(payload["currentOwner"], "currentOwner")
    callback_owner = _token(payload["callbackOwner"], "callbackOwner")
    callback_type = payload["callbackType"]
    if callback_type not in CALLBACK_TYPES:
        raise ValueError("callbackType is not supported")
    recording = _bool(payload["recording"], "recording")
    surface = _token(payload["attachedSurface"], "attachedSurface")
    current_resources = _resources(payload["currentResources"], "currentResources")
    stale_resources = _resources(payload["staleResources"], "staleResources")
    if not current_resources:
        raise ValueError("currentResources must be non-empty")
    overlap = set(current_resources) & set(stale_resources)
    if overlap:
        raise ValueError("a resource cannot belong to both generations")
    if moment in MOMENTS and recording and moment != "before_first_sample":
        # Recording may still be true only if this generation already acknowledged
        # a sample. Late-callback repeats in this case start from a non-recording
        # owner after stop, recreation, or reopen. before_first_sample is never
        # recording. During stopping the indicator is already down.
        if moment in ("during_stopping", "after_activity_recreation", "after_camera_reopen"):
            raise ValueError("recording must be false for this late-callback moment")
    if moment == "before_first_sample" and recording:
        raise ValueError("recording must be false before the first sample")
    return {
        "moment": moment,
        "state": MOMENT_STATE[moment],
        "currentGeneration": current_generation,
        "currentOwner": current_owner,
        "recording": recording,
        "attachedSurface": surface,
        "currentResources": current_resources,
        "callbackGeneration": callback_generation,
        "callbackOwner": callback_owner,
        "callbackType": callback_type,
        "resurrectRecording": _bool(payload["resurrectRecording"], "resurrectRecording"),
        "attachObsoleteSurface": _bool(payload["attachObsoleteSurface"], "attachObsoleteSurface"),
        "staleResources": stale_resources,
    }


def _generation(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive int")
    return value


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _resources(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    seen: set[str] = set()
    items: list[str] = []
    for item in value:
        token = _token(item, name)
        if token in seen:
            raise ValueError(f"{name} must be unique")
        seen.add(token)
        items.append(token)
    return items


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
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
