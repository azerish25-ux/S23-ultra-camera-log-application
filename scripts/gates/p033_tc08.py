"""TC-P033-08 throughput stage conflation.

Acquisition-only speed and saved-source throughput are different stages.
Only a retained complete saved path is reported as that path. Advertising
discarded-frame acquisition speed as saved RAW recording performance fails.
The report is not a physical qualification.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P033-08"
INTERVENTION = "Supply fast acquisition-only evidence but a slower or failing saved-source experiment."
EXPECTED = "Report separate stage rates and qualify only the successfully retained complete path."
NEGATIVE = "Advertising discarded-frame acquisition speed as saved RAW recording performance must fail."
REPEATS = ("increasing duration", "storage pressure", "audio selection", "thermal state")
_DURATIONS = ("short", "increasing")
_THERMAL = ("nominal", "severe")
_FPS = re.compile(r"[1-9][0-9]*")
_PAYLOAD_KEYS = (
    "acquisitionFps",
    "savedFps",
    "savedFailed",
    "discardedFrames",
    "advertiseAcquisitionAsSaved",
    "duration",
    "storagePressure",
    "audioSelected",
    "thermal",
    "retainedComplete",
    "inventory",
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
    """Keep acquisition speed distinct from saved RAW retention."""
    data = _payload(payload)
    reasons = [
        "acquisition " + data["acquisitionFps"],
        "saved " + data["savedFps"],
        "stages are reported separately",
    ]
    rejected: list[str] = []
    if data["advertiseAcquisitionAsSaved"]:
        rejected.append("acquisition-advertised-as-saved")
        reasons.append(NEGATIVE)
    if data["savedFailed"] or not data["retainedComplete"]:
        rejected.append("saved-path-incomplete")
        reasons.append("the saved-source path did not retain a complete recording")
    if data["discardedFrames"] > 0 and data["advertiseAcquisitionAsSaved"]:
        reasons.append("discarded acquisition frames are not saved RAW performance")
    if rejected and data["advertiseAcquisitionAsSaved"]:
        decision = "rejected"
    elif "saved-path-incomplete" in rejected:
        decision = "stages_separated"
        reasons.append(EXPECTED)
        reasons.append("stages_separated does not advertise acquisition speed as saved performance")
    else:
        decision = "retained_complete"
        reasons.append("only the retained complete saved path is reported")
        reasons.append("retained_complete is a host label, not physical qualification, and is not acquisition speed")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-08 must not yield qualified or allowed")
    questions = _questions(data)
    return _result(decision, reasons, rejected, _preserved(data), questions)


def _questions(data: dict) -> list[str]:
    questions = ["acquisition speed is not saved RAW recording performance"]
    if data["duration"] == "increasing":
        questions.append("increasing duration does not merge the two stage rates")
    if data["storagePressure"]:
        questions.append("storage pressure stays on the saved-source stage")
    if data["audioSelected"]:
        questions.append("audio selection does not convert acquisition speed into saved RAW performance")
    if data["thermal"] == "severe":
        questions.append("thermal state does not upgrade a discarded-frame acquisition rate")
    return questions


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    acquisition = _fps(payload["acquisitionFps"], "acquisitionFps")
    saved = _fps(payload["savedFps"], "savedFps")
    discarded = payload["discardedFrames"]
    if type(discarded) is not int or discarded < 0:
        raise ValueError("discardedFrames must be a non-negative int")
    duration = payload["duration"]
    if duration not in _DURATIONS:
        raise ValueError("duration must be short or increasing")
    thermal = payload["thermal"]
    if thermal not in _THERMAL:
        raise ValueError("thermal must be nominal or severe")
    saved_failed = _bool(payload["savedFailed"], "savedFailed")
    retained = _bool(payload["retainedComplete"], "retainedComplete")
    if saved_failed and retained:
        raise ValueError("a failed saved path cannot be a retained complete path")
    return {
        "acquisitionFps": acquisition,
        "savedFps": saved,
        "savedFailed": saved_failed,
        "discardedFrames": discarded,
        "advertiseAcquisitionAsSaved": _bool(
            payload["advertiseAcquisitionAsSaved"], "advertiseAcquisitionAsSaved"
        ),
        "duration": duration,
        "storagePressure": _bool(payload["storagePressure"], "storagePressure"),
        "audioSelected": _bool(payload["audioSelected"], "audioSelected"),
        "thermal": thermal,
        "retainedComplete": retained,
        "inventory": _tokens(payload["inventory"], "inventory"),
    }


def _preserved(data: dict) -> list[str]:
    preserved = list(data["inventory"])
    preserved.extend([
        "acquisition:" + data["acquisitionFps"],
        "saved:" + data["savedFps"],
        "discarded:" + str(data["discardedFrames"]),
        "duration:" + data["duration"],
        "thermal:" + data["thermal"],
        "audio:" + ("selected" if data["audioSelected"] else "unselected"),
        "storage:" + ("pressure" if data["storagePressure"] else "clear"),
    ])
    return preserved


def _fps(value: object, name: str) -> str:
    if not isinstance(value, str) or _FPS.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical positive integer string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    items = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip() or item in seen:
            raise ValueError(f"{name} items must be unique non-empty strings")
        seen.add(item)
        items.append(item)
    return items


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-08 must not yield qualified or allowed")
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
