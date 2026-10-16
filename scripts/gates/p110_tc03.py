"""TC-P110-03 Relative-scale pumping.

Host fixture. Per-frame min-max normalization must not move a stationary background.
"""

from __future__ import annotations

CASE_ID = "TC-P110-03"
NAME = "Relative-scale pumping"
INTERVENTION = "Introduce a near object or scene-content change that alters raw model depth normalization."
EXPECTED = "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts."
NEGATIVE = "Independent min-max normalization per frame must fail."
REPEAT = "Repeat stationary backgrounds with changing foreground occupancy."
NEGATIVE_TOKEN = "independent-minmax-normalization-per-frame"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "frames", "stationary", "normalization")
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


def _frame(values, name: str) -> list[float]:
    _require(isinstance(values, list) and len(values) >= 1, name + " must be a non-empty list")
    numbers: list[float] = []
    for index, item in enumerate(values):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"{name}[{index}] must be a number")
        number = float(item)
        _require(number == number and abs(number) != float("inf"), f"{name}[{index}] must be finite")
        numbers.append(number)
    return numbers


def _scale(frame: list[float], low: float, high: float) -> list[float]:
    span = high - low
    _require(span != 0.0, "degenerate depth range")
    return [(value - low) / span for value in frame]


def normalize_frames(frames: list[list[float]], mode: str) -> list[list[float]]:
    ranges = [(min(frame), max(frame)) for frame in frames]
    if mode == "independent-minmax":
        return [_scale(frame, low, high) for frame, (low, high) in zip(frames, ranges)]
    if mode == "aligned":
        low, high = ranges[0]
        return [_scale(frame, low, high) for frame in frames]
    if mode == "reset":
        # Honest reset: do not invent a new global focus scale.
        return [list(frame) for frame in frames]
    raise ValueError("normalization must be independent-minmax, aligned, or reset")


def stationary_pumped(normalized: list[list[float]], stationary: list[int]) -> bool:
    baseline = [normalized[0][index] for index in stationary]
    for frame in normalized[1:]:
        for index, base in zip(stationary, baseline):
            if frame[index] != base:
                return True
    return False


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    raw_frames = payload["frames"]
    _require(isinstance(raw_frames, list) and len(raw_frames) >= 2, "frames must contain at least 2 frames")
    frames = [_frame(frame, f"frames[{index}]") for index, frame in enumerate(raw_frames)]
    width = len(frames[0])
    _require(all(len(frame) == width for frame in frames), "frames must share a width")
    stationary = payload["stationary"]
    _require(isinstance(stationary, list) and len(stationary) >= 1, "stationary must be a non-empty list")
    _require(all(type(index) is int and 0 <= index < width for index in stationary), "stationary index out of range")
    mode = payload["normalization"]
    normalized = normalize_frames(frames, mode)
    pumped = stationary_pumped(normalized, stationary)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if mode == "independent-minmax" and pumped:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("stationary background moved under per-frame min-max normalization")
    elif mode == "independent-minmax":
        decision = "recorded"
        reasons.append("per-frame min-max did not move the declared stationary samples")
    elif mode == "aligned":
        _require(not pumped, "aligned scale still moved a stationary sample")
        decision = "recorded"
        reasons.append("relative depth stayed on the first frame's scale")
    else:
        decision = "recorded"
        reasons.append("scale reset kept raw relative depth without a global focus shift")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
