"""TC-P103-02 Preprocessing geometry error.

Host fixture. Unrecorded stretching and swapped channels fail closed.
"""

from __future__ import annotations

CASE_ID = "TC-P103-02"
NAME = "Preprocessing geometry error"
INTERVENTION = "Use a non-square source with known corner markers and alter resizing, padding, or channel order."
EXPECTED = "Match the specified tensor preparation and restore output coordinates correctly."
NEGATIVE = "Unrecorded stretching or swapped color channels must fail."
REPEAT = "Repeat portrait, landscape, cropped, and rotated source frames."
NEGATIVE_TOKEN = "unrecorded-stretching-swapped-color-channels-fail"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "sourceWidth",
    "sourceHeight",
    "preparedWidth",
    "preparedHeight",
    "stretchRecorded",
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


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive int")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if type(payload["applyNegative"]) is not bool or type(payload["applyMutant"]) is not bool:
        raise ValueError("flags must be bools")
    if type(payload["stretchRecorded"]) is not bool or type(payload["cornersRestored"]) is not bool:
        raise ValueError("geometry flags must be bools")
    source_w = _positive_int(payload["sourceWidth"], "sourceWidth")
    source_h = _positive_int(payload["sourceHeight"], "sourceHeight")
    prepared_w = _positive_int(payload["preparedWidth"], "preparedWidth")
    prepared_h = _positive_int(payload["preparedHeight"], "preparedHeight")
    channel_order = _text(payload["channelOrder"], "channelOrder")
    expected_order = _text(payload["expectedChannelOrder"], "expectedChannelOrder")
    source_aspect = source_w / source_h
    prepared_aspect = prepared_w / prepared_h
    aspect_changed = abs(source_aspect - prepared_aspect) > 1e-9
    unrecorded_stretch = aspect_changed and payload["stretchRecorded"] is not True
    channels_swapped = channel_order != expected_order
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"source={source_w}x{source_h}; prepared={prepared_w}x{prepared_h}",
        f"aspectChanged={aspect_changed}; stretchRecorded={payload['stretchRecorded']}",
        f"channelOrder={channel_order}; expectedChannelOrder={expected_order}",
    ]
    rejected: list[str] = []
    if payload["applyMutant"] or payload["applyNegative"] or unrecorded_stretch or channels_swapped:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["cornersRestored"] is not True:
        rejected.append("output-coordinates-not-restored")
        reasons.append("corner markers were not restored to output coordinates")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("tensor preparation matches and output coordinates are restored")
        reasons.append("narrower software result retained; physical behavior stays open")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
