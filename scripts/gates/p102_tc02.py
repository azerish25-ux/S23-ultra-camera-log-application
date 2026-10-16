"""TC-P102-02 Preprocessing geometry error.

Host reference. Corner markers on a non-square frame are mapped by an integer
scale and pad. Unrecorded non-uniform scale, or a channel order other than
RGB, is rejected. Restored corners must equal the source markers.
"""

from __future__ import annotations

CASE_ID = "TC-P102-02"
NAME = "Preprocessing geometry error"
INTERVENTION = "Use a non-square source with known corner markers and alter resizing, padding, or channel order."
EXPECTED = "Match the specified tensor preparation and restore output coordinates correctly."
NEGATIVE = "Unrecorded stretching or swapped color channels must fail."
REPEAT = "Repeat portrait, landscape, cropped, and rotated source frames."
NEGATIVE_TOKEN = "unrecorded-stretching-swapped-color-channels-fail"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "width",
    "height",
    "scaleX",
    "scaleY",
    "padX",
    "padY",
    "channelOrder",
    "stretchRecorded",
    "outputCorners",
    "restoredCorners",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _positive(value: object, label: str) -> int:
    _require(type(value) is int and value >= 1, label + " must be a positive int")
    return value


def _pad(value: object, label: str) -> int:
    _require(type(value) is int and value >= 0, label + " must be a non-negative int")
    return value


def _points(value: object, label: str) -> list[tuple[int, int]]:
    _require(isinstance(value, list) and len(value) == 4, label + " must contain 4 points")
    points: list[tuple[int, int]] = []
    for item in value:
        _require(isinstance(item, list) and len(item) == 2, label + " point must be [x, y]")
        x, y = item
        _require(type(x) is int and type(y) is int, label + " coordinates must be ints")
        points.append((x, y))
    return points


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    width = _positive(payload["width"], "width")
    height = _positive(payload["height"], "height")
    _require(width != height, "source must be non-square")
    _require(width >= 2 and height >= 2, "source must have a far corner")
    scale_x = _positive(payload["scaleX"], "scaleX")
    scale_y = _positive(payload["scaleY"], "scaleY")
    pad_x = _pad(payload["padX"], "padX")
    pad_y = _pad(payload["padY"], "padY")
    channel = payload["channelOrder"]
    _require(isinstance(channel, str) and len(channel) == 3 and set(channel) <= set("RGB"),
             "channelOrder must be a 3-letter RGB permutation")
    _require(type(payload["stretchRecorded"]) is bool, "stretchRecorded must be a bool")
    output = _points(payload["outputCorners"], "outputCorners")
    restored = _points(payload["restoredCorners"], "restoredCorners")

    markers = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    expected_output = [(x * scale_x + pad_x, y * scale_y + pad_y) for x, y in markers]
    rejected: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, f"repeat {repeat}"]
    stretched = scale_x != scale_y
    if stretched and not payload["stretchRecorded"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append(f"non-uniform scale {scale_x}:{scale_y} was not recorded")
    if channel != "RGB":
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("channel order " + channel + " is not RGB")
    if output != expected_output:
        rejected.append("preparation-does-not-match-declared-geometry")
        reasons.append("output corners do not match scale and pad")
    if restored != markers:
        rejected.append("coordinates-not-restored")
        reasons.append("restored corners do not match the source markers")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append(
            f"restored {width}x{height} markers with scale {scale_x},{scale_y} pad {pad_x},{pad_y}"
        )
    return _finish(decision, reasons, rejected, evidence, [f"{width}x{height}"])


def _finish(decision: str, reasons: list[str], rejected: list[str], evidence: str, extra: list[str]) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, *extra],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
