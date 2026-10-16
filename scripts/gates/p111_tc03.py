"""TC-P111-03 Relative-scale pumping.

Host fixture. Independent per-frame min-max normalization is computed and rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P111-03"
NAME = "Relative-scale pumping"
INTERVENTION = "Introduce a near object or scene-content change that alters raw model depth normalization."
EXPECTED = "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts."
NEGATIVE = "Independent min-max normalization per frame must fail."
REPEAT = "Repeat stationary backgrounds with changing foreground occupancy."
NEGATIVE_TOKEN = "independent-minmax-normalization"
PAYLOAD_KEYS = ("evidenceId", "repeat", "normalization", "stationaryIndex", "frames")
NORMALIZATIONS = {"independent-minmax", "shared-scale", "honest-reset"}
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


def _text(value, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _depths(frames: list) -> list[list[float]]:
    parsed: list[list[float]] = []
    width = None
    for index, frame in enumerate(frames):
        _require(isinstance(frame, list) and len(frame) >= 2, f"frame {index} must contain at least 2 depths")
        if width is None:
            width = len(frame)
        _require(len(frame) == width, "frames must share a depth width")
        row = []
        for sample_index, sample in enumerate(frame):
            _require(isinstance(sample, (int, float)) and not isinstance(sample, bool), "depth must be a number")
            value = float(sample)
            _require(value > 0.0 and value == value and value not in {float("inf"), float("-inf")}, "depth must be finite and > 0")
            row.append(value)
        if min(row) == max(row):
            raise ValueError(f"frame {index} depth is degenerate")
        parsed.append(row)
    return parsed


def _normalize(row: list[float], low: float, high: float) -> list[float]:
    span = high - low
    return [(value - low) / span for value in row]


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    mode = payload["normalization"]
    _require(mode in NORMALIZATIONS, "normalization is invalid")
    frames = payload["frames"]
    _require(isinstance(frames, list) and len(frames) >= 2, "frames must contain at least 2 frames")
    parsed = _depths(frames)
    index = payload["stationaryIndex"]
    _require(type(index) is int and 0 <= index < len(parsed[0]), "stationaryIndex is invalid")
    raw = [row[index] for row in parsed]
    if mode == "independent-minmax":
        normalized = [_normalize(row, min(row), max(row)) for row in parsed]
    elif mode == "shared-scale":
        low = min(min(row) for row in parsed)
        high = max(max(row) for row in parsed)
        normalized = [_normalize(row, low, high) for row in parsed]
    else:
        normalized = parsed
    stationary = [row[index] for row in normalized]
    pumped = max(stationary) - min(stationary)
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        "stationary_raw:" + ",".join(format(value, ".12g") for value in raw),
        "stationary_normalized:" + ",".join(format(value, ".12g") for value in stationary),
        f"pump={format(pumped, '.12g')}",
    ]
    rejected: list[str] = []
    if mode == "independent-minmax":
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("independent min-max normalization changes the global focus scale")
    elif mode == "shared-scale" and pumped > 1e-9:
        decision = "rejected"
        rejected.append("unstable-shared-scale")
        reasons.append("shared scale did not keep the stationary depth aligned")
    else:
        decision = "recorded"
        if mode == "honest-reset":
            reasons.append("scale reset honestly without an independent min-max focus shift")
        else:
            reasons.append("shared scale kept the stationary depth aligned")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"pump:{format(pumped, '.12g')}"],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
