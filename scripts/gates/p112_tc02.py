"""TC-P112-02 Disoccluded background.

Host fixture. Newly visible pixels must take current depth, not the old
foreground depth left behind by history. This is not an applyNegative stub.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P112-02"
PHASE = "P112"
WORKSTREAM = 14
NAME = "Disoccluded background"
INTERVENTION = "Reveal new background behind a moving foreground object where historical depth is invalid."
EXPECTED = "Use current evidence and uncertainty rather than smearing previous foreground values into the new region."
NEGATIVE = "Filling all newly visible pixels with old depth must fail."
REPEAT = "Repeat thin objects, hands, hair, and large foreground occluders."
NEGATIVE_TOKEN = "filled-newly-visible-pixels-with-old-depth"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = {"evidenceId", "repeat", "pixels"}
PIXEL_KEYS = {"newly_visible", "historical_depth", "current_depth", "filled_depth", "uncertainty"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_MATCH = 1e-6


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str, minimum: float | None = None) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number), label + " must be finite")
    if minimum is not None:
        _require(number >= minimum, label + " must be >= " + str(minimum))
    return number


def _text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(),
             label + " must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    _require(type(value) is bool, label + " must be a bool")
    return value


def _pixels(value: object) -> list[dict[str, float | bool]]:
    _require(isinstance(value, list) and value, "pixels must be a non-empty list")
    parsed: list[dict[str, float | bool]] = []
    for index, pixel in enumerate(value):
        _require(isinstance(pixel, dict), f"pixel {index} must be an object")
        missing = PIXEL_KEYS - set(pixel)
        extra = set(pixel) - PIXEL_KEYS
        _require(not missing, f"pixel {index} missing fields: " + ", ".join(sorted(missing)))
        _require(not extra, f"pixel {index} has unexpected fields: " + ", ".join(sorted(extra)))
        parsed.append({
            "newly_visible": _bool(pixel["newly_visible"], f"pixel {index} newly_visible"),
            "historical_depth": _number(pixel["historical_depth"], f"pixel {index} historical_depth"),
            "current_depth": _number(pixel["current_depth"], f"pixel {index} current_depth"),
            "filled_depth": _number(pixel["filled_depth"], f"pixel {index} filled_depth"),
            "uncertainty": _number(pixel["uncertainty"], f"pixel {index} uncertainty", minimum=0.0),
        })
    return parsed


def evaluate(payload: dict) -> dict:
    """Reject disoccluded pixels filled from historical foreground depth."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    pixels = _pixels(payload["pixels"])
    smeared: list[int] = []
    for index, pixel in enumerate(pixels):
        if not pixel["newly_visible"]:
            continue
        filled = float(pixel["filled_depth"])
        current = float(pixel["current_depth"])
        historical = float(pixel["historical_depth"])
        uses_current = abs(filled - current) <= _MATCH
        uses_old = abs(filled - historical) <= _MATCH and abs(historical - current) > _MATCH
        if uses_old or not uses_current:
            smeared.append(index)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if smeared:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("old depth filled newly visible pixels " + ",".join(str(index) for index in smeared))
    else:
        decision = "recorded"
        reasons.append("newly visible pixels use current depth and declared uncertainty")
    preserved = [evidence]
    for index, pixel in enumerate(pixels):
        preserved.append(
            f"pixel:{index}:new={str(pixel['newly_visible']).lower()}:"
            f"historical={pixel['historical_depth']}:current={pixel['current_depth']}:"
            f"filled={pixel['filled_depth']}:uncertainty={pixel['uncertainty']}"
        )
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"} and decision not in {"qualified", "allowed"},
             "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
