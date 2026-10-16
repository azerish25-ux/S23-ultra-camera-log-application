"""TC-P125-01 Ambiguous imported signal.

Host fixture. Detected color, rotation, and timing facts stay separate from
user interpretation. A filename extension does not set transfer or dynamic range.
"""

from __future__ import annotations


CASE_ID = "TC-P125-01"
NAME = "Ambiguous imported signal"
INTERVENTION = "Import media with absent or contradictory color tags, rotation, or timing metadata."
EXPECTED = "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type."
NEGATIVE = "Filename extension alone must not determine transfer or dynamic range."
REPEAT = "Repeat HDR-looking untagged clips, variable rates, and portrait rotation."
FILENAME_TOKEN = "filename-extension-determines-transfer-or-dynamic-range"
SILENT_TOKEN = "silent-normalization"
REPEATS = ("hdr-looking-untagged", "variable-rates", "portrait-rotation")
ROTATIONS = (0, 90, 180, 270)
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filenameExtension",
    "colorTag",
    "detectedTransfer",
    "interpretedTransfer",
    "detectedDynamicRange",
    "interpretedDynamicRange",
    "rotationDegrees",
    "interpretedRotation",
    "timingRate",
    "interpretedTimingRate",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _optional_rotation(value: object, label: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value not in ROTATIONS:
        raise ValueError(f"{label} must be null or one of 0, 90, 180, 270")
    return value


def _from_extension(interpreted: str | None, extension: str, detected: str | None) -> bool:
    if interpreted is None or interpreted != extension:
        return False
    return detected != extension


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    extension = _text(payload["filenameExtension"], "filenameExtension")
    color_tag = _optional_text(payload["colorTag"], "colorTag")
    detected_transfer = _optional_text(payload["detectedTransfer"], "detectedTransfer")
    interpreted_transfer = _optional_text(payload["interpretedTransfer"], "interpretedTransfer")
    detected_range = _optional_text(payload["detectedDynamicRange"], "detectedDynamicRange")
    interpreted_range = _optional_text(payload["interpretedDynamicRange"], "interpretedDynamicRange")
    rotation = _optional_rotation(payload["rotationDegrees"], "rotationDegrees")
    interpreted_rotation = _optional_rotation(payload["interpretedRotation"], "interpretedRotation")
    timing = _optional_text(payload["timingRate"], "timingRate")
    interpreted_timing = _optional_text(payload["interpretedTimingRate"], "interpretedTimingRate")
    rejected: list[str] = []
    if _from_extension(interpreted_transfer, extension, detected_transfer) or _from_extension(
        interpreted_range, extension, detected_range
    ):
        rejected.append(FILENAME_TOKEN)
    silent = (
        (detected_transfer is None and interpreted_transfer is not None)
        or (detected_range is None and interpreted_range is not None)
        or (rotation is None and interpreted_rotation is not None)
        or (timing is None and interpreted_timing is not None)
    )
    if silent and SILENT_TOKEN not in rejected:
        rejected.append(SILENT_TOKEN)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    if FILENAME_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if SILENT_TOKEN in rejected:
        reasons.append("absent metadata was not normalized to an assumed source type")
    if not rejected:
        reasons.append("detected facts stayed separate from user interpretation")
    preserved = [
        evidence,
        {
            "filenameExtension": extension,
            "colorTag": color_tag,
            "detectedTransfer": detected_transfer,
            "interpretedTransfer": interpreted_transfer,
            "detectedDynamicRange": detected_range,
            "interpretedDynamicRange": interpreted_range,
            "rotationDegrees": rotation,
            "interpretedRotation": interpreted_rotation,
            "timingRate": timing,
            "interpretedTimingRate": interpreted_timing,
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved)


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    if decision == "recorded" and rejected:
        raise ValueError("recorded result cannot reject claims")
    if decision == "rejected" and not rejected:
        raise ValueError("rejected result needs a rejected claim")
    return result
