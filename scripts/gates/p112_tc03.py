"""TC-P112-03 Relative-scale pumping.

Host fixture. Per-frame min-max normalization that shifts a stable background
is rejected. An explicit reset may start a new scale. This is not an applyNegative stub.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P112-03"
PHASE = "P112"
WORKSTREAM = 14
NAME = "Relative-scale pumping"
INTERVENTION = "Introduce a near object or scene-content change that alters raw model depth normalization."
EXPECTED = "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts."
NEGATIVE = "Independent min-max normalization per frame must fail."
REPEAT = "Repeat stationary backgrounds with changing foreground occupancy."
NEGATIVE_TOKEN = "independent-minmax-normalization-per-frame"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = {"evidenceId", "repeat", "frames"}
FRAME_KEYS = {"depths", "normalized", "reset"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOL = 1e-9


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number), label + " must be finite")
    return number


def _text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(),
             label + " must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    _require(type(value) is bool, label + " must be a bool")
    return value


def normalize_to_span(depths: list[float], low: float, high: float) -> list[float]:
    """Map depths through one declared [low, high] span. Zero span is invalid."""
    span = high - low
    _require(span != 0.0, "depth span must be non-zero")
    return [(value - low) / span for value in depths]


def _close(left: list[float], right: list[float]) -> bool:
    return len(left) == len(right) and all(abs(a - b) <= _TOL for a, b in zip(left, right))


def _frames(value: object) -> list[dict]:
    _require(isinstance(value, list) and len(value) >= 2, "frames must contain at least 2 objects")
    parsed: list[dict] = []
    for index, frame in enumerate(value):
        _require(isinstance(frame, dict), f"frame {index} must be an object")
        missing = FRAME_KEYS - set(frame)
        extra = set(frame) - FRAME_KEYS
        _require(not missing, f"frame {index} missing fields: " + ", ".join(sorted(missing)))
        _require(not extra, f"frame {index} has unexpected fields: " + ", ".join(sorted(extra)))
        depths_raw = frame["depths"]
        normalized_raw = frame["normalized"]
        _require(isinstance(depths_raw, list) and len(depths_raw) >= 2, f"frame {index} depths need 2 samples")
        _require(isinstance(normalized_raw, list) and len(normalized_raw) == len(depths_raw),
                 f"frame {index} normalized length must match depths")
        depths = [_number(item, f"frame {index} depth {sample}") for sample, item in enumerate(depths_raw)]
        normalized = [
            _number(item, f"frame {index} normalized {sample}") for sample, item in enumerate(normalized_raw)
        ]
        parsed.append({
            "depths": depths,
            "normalized": normalized,
            "reset": _bool(frame["reset"], f"frame {index} reset"),
        })
    return parsed


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def evaluate(payload: dict) -> dict:
    """Reject independent per-frame min-max normalization. Allow a locked scale or an honest reset."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    frames = _frames(payload["frames"])
    reference: tuple[float, float] | None = None
    failures: list[str] = []
    for frame in frames:
        depths = frame["depths"]
        low = min(depths)
        high = max(depths)
        own = normalize_to_span(depths, low, high)
        if reference is None:
            reference = (low, high)
        ref_low, ref_high = reference
        locked = normalize_to_span(depths, ref_low, ref_high)
        scale_changed = (low, high) != (ref_low, ref_high)
        if frame["reset"]:
            if not _close(frame["normalized"], own):
                failures.append("reset-does-not-match-frame-scale")
            reference = (low, high)
        elif _close(frame["normalized"], own) and scale_changed:
            failures.append(NEGATIVE_TOKEN)
        elif _close(frame["normalized"], locked):
            continue
        else:
            failures.append("relative-depth-not-aligned")
    rejected = _unique(failures)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    if rejected:
        decision = "rejected"
        if NEGATIVE_TOKEN in rejected:
            reasons.append(NEGATIVE)
        reasons.append("normalization failures: " + ",".join(rejected))
    else:
        decision = "recorded"
        reasons.append("relative depth stayed on one scale or reset explicitly")
    preserved = [evidence]
    for index, frame in enumerate(frames):
        preserved.append(
            f"frame:{index}:reset={str(frame['reset']).lower()}:"
            f"low={min(frame['depths'])}:high={max(frame['depths'])}"
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
