"""TC-P109-01 History without reprojection.

Host fixture. Unaligned stationary averages are rejected from the depth arrays.
A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P109-01"
NAME = "History without reprojection"
INTERVENTION = "Move a known object while previous depth remains in its original pixel coordinates."
EXPECTED = "Reject unaligned history or warp it correctly before temporal blending."
NEGATIVE = "A stationary-pixel average that leaves depth trails must fail."
REPEAT = "Repeat translation, rotation, scale change, and camera motion."
NEGATIVE_TOKEN = "stationary-pixel-average-depth-trails"
PAYLOAD_KEYS = ("evidenceId", "repeat", "shiftSamples", "historyMode", "previousDepth", "currentDepth")
HISTORY_MODES = ("rejected", "warped", "stationary-average")
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


def _depths(value: object, message: str) -> list[float]:
    _require(isinstance(value, list) and len(value) >= 1, message)
    numbers: list[float] = []
    for index, item in enumerate(value):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"{message} {index}")
        number = float(item)
        _require(number == number and number not in (float("inf"), float("-inf")), f"{message} {index}")
        numbers.append(number)
    return numbers


def _warp(previous: list[float], shift: int) -> list[float | None]:
    warped: list[float | None] = [None] * len(previous)
    for index, value in enumerate(previous):
        target = index + shift
        if 0 <= target < len(previous):
            warped[target] = value
    return warped


def _finish(evidence: str, repeat: str, decision: str, rejected: list[str], detail: str) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(decision not in {"qualified", "allowed"}, "negative or unmeasured result must not be qualified")
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, detail]
    if decision == "rejected":
        reasons.append(NEGATIVE)
    else:
        reasons.append("narrower software result retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    shift = payload["shiftSamples"]
    _require(type(shift) is int, "shiftSamples must be an int")
    mode = payload["historyMode"]
    _require(mode in HISTORY_MODES, "historyMode is invalid")
    previous = _depths(payload["previousDepth"], "previousDepth")
    current = _depths(payload["currentDepth"], "currentDepth")
    _require(len(previous) == len(current), "depth arrays must have the same length")
    if mode == "stationary-average":
        averaged = [(previous[index] + current[index]) / 2.0 for index in range(len(previous))]
        trails = [index for index, value in enumerate(averaged) if value != current[index]]
        detail = (
            f"stationary average at the original coordinates after shift {shift}; "
            f"trail indexes {','.join(str(index) for index in trails) if trails else 'none'}"
        )
        if shift != 0:
            return _finish(evidence, repeat, "rejected", [NEGATIVE_TOKEN], detail)
        return _finish(evidence, repeat, "recorded", [], detail)
    if mode == "warped":
        warped = _warp(previous, shift)
        landed = sum(item is not None for item in warped)
        detail = f"history warped by {shift} samples before blending; in-frame {landed}"
        return _finish(evidence, repeat, "recorded", [], detail)
    detail = f"unaligned history rejected before blending; shift {shift} was not averaged in place"
    return _finish(evidence, repeat, "recorded", [], detail)
