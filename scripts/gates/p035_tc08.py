"""TC-P035-08 throughput stage conflation.

Intervention: Supply fast acquisition-only evidence but a slower or failing
saved-source experiment.
Expected: Report separate stage rates and qualify only the successfully
retained complete path.
Negative: Advertising discarded-frame acquisition speed as saved RAW recording
performance must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P035-08"
INTERVENTION = (
    "Supply fast acquisition-only evidence but a slower or failing saved-source experiment."
)
EXPECTED = (
    "Report separate stage rates and qualify only the successfully retained complete path."
)
NEGATIVE = (
    "Advertising discarded-frame acquisition speed as saved RAW recording performance must fail."
)

STATUSES = ("complete", "failed", "slower")
DURATIONS = ("short", "increasing")
THERMALS = ("nominal", "severe")
FPS = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_PAYLOAD_KEYS = (
    "acquisitionFps",
    "savedFps",
    "savedStatus",
    "discardedFrames",
    "advertiseAcquisitionAsSaved",
    "duration",
    "storagePressure",
    "audioSelected",
    "thermal",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "retained_path", "stage_separated")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep acquisition and saved-source rates apart. Neither rate is qualification."""
    (
        acquisition,
        saved,
        status,
        discarded,
        advertise,
        duration,
        storage,
        audio,
        thermal,
    ) = _payload(payload)
    preserved = [
        f"acquisition:{acquisition}",
        f"saved:{saved}",
        f"duration:{duration}",
        f"thermal:{thermal}",
    ]
    if advertise:
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "acquisition fps was not published as the saved rate"],
            ["acquisition-advertised-as-saved"],
            preserved,
            ["stages remain separate"],
        )
    clean = (
        status == "complete"
        and not discarded
        and not storage
        and not audio
        and thermal == "nominal"
    )
    questions = ["host label is not physical S23 qualification"]
    if duration == "increasing":
        questions.append("increasing duration is not a measured cadence")
    if storage:
        questions.append("storage pressure")
    if audio:
        questions.append("audio selected")
    if thermal == "severe":
        questions.append("thermal severe")
    if discarded:
        questions.append("discarded frames")
    if status != "complete":
        questions.append(f"saved status {status}")
    if clean:
        return _result(
            "retained_path",
            [
                EXPECTED,
                "only the retained saved path is reported as complete",
                "acquisition rate stays a separate stage",
                "retained_path is not physical S23 qualification",
            ],
            [],
            preserved,
            questions,
        )
    return _result(
        "stage_separated",
        [EXPECTED, "stage rates stay separate when the saved path is not cleanly retained"],
        [],
        preserved,
        questions,
    )


def _fps(value: object, label: str, allow_zero: bool) -> str:
    if not isinstance(value, str) or FPS.fullmatch(value) is None:
        raise ValueError(label)
    if value == "0" and not allow_zero:
        raise ValueError(label + " must be positive")
    return value


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload")
    status = payload["savedStatus"]
    duration = payload["duration"]
    thermal = payload["thermal"]
    if status not in STATUSES or duration not in DURATIONS or thermal not in THERMALS:
        raise ValueError("status, duration, or thermal")
    acquisition = _fps(payload["acquisitionFps"], "acquisitionFps", False)
    saved = _fps(payload["savedFps"], "savedFps", status == "failed")
    if status == "complete" and saved == "0":
        raise ValueError("a complete save cannot report zero fps")
    discarded = payload["discardedFrames"]
    advertise = payload["advertiseAcquisitionAsSaved"]
    storage = payload["storagePressure"]
    audio = payload["audioSelected"]
    if any(type(flag) is not bool for flag in (discarded, advertise, storage, audio)):
        raise ValueError("flags")
    return acquisition, saved, status, discarded, advertise, duration, storage, audio, thermal


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("throughput decision cannot be qualified or allowed")
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
