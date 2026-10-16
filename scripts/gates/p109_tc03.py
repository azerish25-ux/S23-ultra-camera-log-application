"""TC-P109-03 Relative-scale pumping.

Host fixture. Independent per-frame min-max normalization is rejected.
A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P109-03"
NAME = "Relative-scale pumping"
INTERVENTION = "Introduce a near object or scene-content change that alters raw model depth normalization."
EXPECTED = "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts."
NEGATIVE = "Independent min-max normalization per frame must fail."
REPEAT = "Repeat stationary backgrounds with changing foreground occupancy."
NEGATIVE_TOKEN = "independent-minmax-normalization"
PAYLOAD_KEYS = ("evidenceId", "repeat", "mode", "frames")
MODES = ("shared", "reset", "per-frame-minmax")
FRAME_KEYS = {"background", "foreground"}
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


def _series(value: object, message: str) -> list[float]:
    _require(isinstance(value, list) and len(value) >= 1, message)
    numbers: list[float] = []
    for index, item in enumerate(value):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"{message} {index}")
        number = float(item)
        _require(number == number and number not in (float("inf"), float("-inf")), f"{message} {index}")
        numbers.append(number)
    return numbers


def _normalize(values: list[float], low: float, high: float) -> list[float]:
    span = high - low
    if span == 0.0:
        return [0.0 for _ in values]
    return [(value - low) / span for value in values]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


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
    mode = payload["mode"]
    _require(mode in MODES, "mode is invalid")
    frames = payload["frames"]
    _require(isinstance(frames, list) and len(frames) >= 2, "frames must contain at least 2 items")
    parsed: list[tuple[list[float], list[float]]] = []
    for index, frame in enumerate(frames):
        _require(isinstance(frame, dict) and set(frame) == FRAME_KEYS, f"frame {index} keys")
        background = _series(frame["background"], f"frame {index} background")
        foreground = _series(frame["foreground"], f"frame {index} foreground")
        parsed.append((background, foreground))
    if mode == "reset":
        detail = "history reset honestly; no per-frame min-max and no invented global focus shift"
        return _finish(evidence, repeat, "recorded", [], detail)
    if mode == "per-frame-minmax":
        means: list[str] = []
        for background, foreground in parsed:
            pool = background + foreground
            normalized = _normalize(background, min(pool), max(pool))
            means.append(f"{_mean(normalized):.6f}")
        detail = "per-frame min-max normalized-background " + ",".join(means)
        return _finish(evidence, repeat, "rejected", [NEGATIVE_TOKEN], detail)
    pool = [value for background, foreground in parsed for value in background + foreground]
    low = min(pool)
    high = max(pool)
    means = []
    for background, _foreground in parsed:
        normalized = _normalize(background, low, high)
        means.append(f"{_mean(normalized):.6f}")
    detail = "shared-scale normalized-background " + ",".join(means)
    return _finish(evidence, repeat, "recorded", [], detail)
