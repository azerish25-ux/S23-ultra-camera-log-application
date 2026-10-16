"""TC-P112-07 Bokeh ordering and leakage.

Host fixture. Uniform background blur with no foreground coverage model is
rejected. Coverage is bounded to normalized energy in [0, 1]. Leakage above
the declared limit is rejected. This is not an applyNegative stub.
"""

from __future__ import annotations

import math
import statistics

CASE_ID = "TC-P112-07"
PHASE = "P112"
WORKSTREAM = 14
NAME = "Bokeh ordering and leakage"
INTERVENTION = "Render strong foreground defocus with bright lights behind an in-focus opaque subject."
EXPECTED = "Respect layering and normalized energy while declaring unavoidable missing-background approximations."
NEGATIVE = "Uniform background blur with no foreground coverage model must fail."
REPEAT = "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem."
NEGATIVE_TOKEN = "uniform-background-blur-without-foreground-coverage"
MISSING_TOKEN = "missing-foreground-coverage-model"
LEAK_TOKEN = "bokeh-leakage-exceeds-declared-limit"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = {"evidenceId", "repeat", "background_blur", "foreground_coverage", "leakage", "leakage_limit"}
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


def _number(value: object, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number), label + " must be finite")
    if minimum is not None:
        _require(number >= minimum, label + " must be >= " + str(minimum))
    if maximum is not None:
        _require(number <= maximum, label + " must be <= " + str(maximum))
    return number


def _text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(),
             label + " must be a non-empty string")
    return value


def _series(value: object, label: str, minimum: float, maximum: float | None, minimum_count: int) -> list[float]:
    _require(isinstance(value, list) and len(value) >= minimum_count, label + " length is invalid")
    return [
        _number(item, f"{label} {index}", minimum=minimum, maximum=maximum)
        for index, item in enumerate(value)
    ]


def evaluate(payload: dict) -> dict:
    """Reject uniform blur that has no coverage model, and reject leakage over the limit."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    blur = _series(payload["background_blur"], "background_blur", 0.0, None, 2)
    coverage = _series(payload["foreground_coverage"], "foreground_coverage", 0.0, 1.0, 0)
    leakage = _number(payload["leakage"], "leakage", minimum=0.0)
    leakage_limit = _number(payload["leakage_limit"], "leakage_limit", minimum=0.0)
    uniform = float(statistics.pstdev(blur)) == 0.0
    energy = float(math.fsum(coverage))
    no_coverage = len(coverage) == 0 or energy == 0.0
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"coverage_energy={energy!r}",
        "foreground coverage energy is normalized per sample to [0, 1]",
    ]
    rejected: list[str] = []
    if no_coverage and uniform:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif no_coverage:
        rejected.append(MISSING_TOKEN)
        reasons.append("foreground coverage model is missing")
    elif leakage > leakage_limit:
        rejected.append(LEAK_TOKEN)
        reasons.append("background leakage through the opaque subject exceeds the declared limit")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("layering kept a coverage model and leakage stayed inside the declared limit")
    preserved = [
        evidence,
        f"coverage_energy={energy!r}",
        f"background_blur_pstdev={float(statistics.pstdev(blur))!r}",
        f"leakage={leakage!r}",
        f"uniform={'true' if uniform else 'false'}",
    ]
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
