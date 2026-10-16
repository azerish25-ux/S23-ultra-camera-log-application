"""TC-P104-02 Preprocessing geometry error.

Non-square sources must keep a recorded geometry transform and channel order.
Unrecorded stretching or swapped channels fail. Corner coordinates must be restored.
"""

from __future__ import annotations


CASE_ID = "TC-P104-02"
NAME = "Preprocessing geometry error"
INTERVENTION = "Use a non-square source with known corner markers and alter resizing, padding, or channel order."
EXPECTED = "Match the specified tensor preparation and restore output coordinates correctly."
NEGATIVE = "Unrecorded stretching or swapped color channels must fail."
REPEAT = "Repeat portrait, landscape, cropped, and rotated source frames."
NEGATIVE_TOKEN = "unrecorded-stretching-or-swapped-color-channels"
OPEN_QUESTION = "physical S23 measurement was not run"
ORIENTATIONS = ("portrait", "landscape", "cropped", "rotated")
RESIZES = ("letterbox", "stretch", "crop", "pad")
CHANNELS = ("rgb", "bgr")
PAYLOAD_KEYS = (
    "evidenceId",
    "orientation",
    "sourceWidth",
    "sourceHeight",
    "resize",
    "geometryRecorded",
    "channelOrder",
    "expectedChannelOrder",
    "cornersRestored",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    (
        evidence,
        orientation,
        width,
        height,
        resize,
        recorded,
        channel,
        expected,
        corners,
    ) = _payload(payload)
    rejected: list[str] = []
    if resize == "stretch" and not recorded:
        rejected.append(NEGATIVE_TOKEN)
    if channel != expected:
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
    if not corners:
        rejected.append("corners-not-restored")
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    if rejected:
        reasons.append(NEGATIVE)
    else:
        reasons.append(f"{orientation} {width}x{height} {resize} kept geometry and {channel} order")
    preserved = [
        evidence,
        f"orientation:{orientation}",
        f"source:{width}x{height}",
        f"resize:{resize}",
        f"geometry-recorded:{str(recorded).lower()}",
        f"channel-order:{channel}",
        f"expected-channel-order:{expected}",
        f"corners-restored:{str(corners).lower()}",
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, evidence)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    orientation = payload["orientation"]
    if orientation not in ORIENTATIONS:
        raise ValueError("orientation is unsupported")
    width = _positive_int(payload["sourceWidth"], "sourceWidth")
    height = _positive_int(payload["sourceHeight"], "sourceHeight")
    if width == height:
        raise ValueError("source must be non-square")
    resize = payload["resize"]
    if resize not in RESIZES:
        raise ValueError("resize is unsupported")
    channel = payload["channelOrder"]
    expected = payload["expectedChannelOrder"]
    if channel not in CHANNELS or expected not in CHANNELS:
        raise ValueError("channel order is unsupported")
    return (
        evidence,
        orientation,
        width,
        height,
        resize,
        _bool(payload["geometryRecorded"], "geometryRecorded"),
        channel,
        expected,
        _bool(payload["cornersRestored"], "cornersRestored"),
    )


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(label + " must be a non-empty string")
    return value


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(label + " must be a positive int")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(label + " must be a bool")
    return value


def _finish(decision: str, reasons: list[str], rejected: list[str], preserved: list[str], evidence: str) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
