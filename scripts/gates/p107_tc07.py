"""TC-P107-07 Bokeh ordering and leakage.

Host reference. Layer order and energy must hold. Uniform blur without a
coverage model is rejected.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P107-07"
NAME = "Bokeh ordering and leakage"
INTERVENTION = "Render strong foreground defocus with bright lights behind an in-focus opaque subject."
EXPECTED = "Respect layering and normalized energy while declaring unavoidable missing-background approximations."
NEGATIVE = "Uniform background blur with no foreground coverage model must fail."
REPEAT = "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem."
NEGATIVE_TOKEN = "uniform-background-blur"
ENERGY_TOLERANCE = 1e-6
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "uniform_background_blur",
    "foreground_coverage_model",
    "subject_coverage",
    "background_energy",
    "foreground_energy",
    "missing_background_declared",
    "subject_in_front",
)
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


def _number(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    value_f = float(value)
    _require(math.isfinite(value_f), f"{label} must be finite")
    return value_f


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(), "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    for name in ("uniform_background_blur", "foreground_coverage_model", "missing_background_declared", "subject_in_front"):
        _require(type(payload[name]) is bool, f"{name} must be a bool")
    coverage = _number(payload["subject_coverage"], "subject_coverage")
    background = _number(payload["background_energy"], "background_energy")
    foreground = _number(payload["foreground_energy"], "foreground_energy")
    _require(0.0 <= coverage <= 1.0, "subject_coverage must lie in [0, 1]")
    _require(background >= 0.0 and foreground >= 0.0, "energy must be non-negative")
    composite = coverage * foreground + (1.0 - coverage) * background
    energy_sum = foreground + background
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"composite_energy={format(composite, '.12g')}",
        f"energy_sum={format(energy_sum, '.12g')}",
    ]
    rejected: list[str] = []
    if payload["uniform_background_blur"] and not payload["foreground_coverage_model"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not payload["subject_in_front"]:
        rejected.append("layer-order")
        reasons.append("in-focus subject is not in front of the background lights")
    normalized = abs(energy_sum - 1.0) <= ENERGY_TOLERANCE
    if not normalized and not payload["missing_background_declared"]:
        rejected.append("energy-not-normalized")
        reasons.append("layer energy is not normalized and the missing background is undeclared")
    if payload["missing_background_declared"]:
        reasons.append("missing-background approximation declared")
    if coverage >= 1.0 - ENERGY_TOLERANCE and background > ENERGY_TOLERANCE and not payload["foreground_coverage_model"]:
        if "background-leakage" not in rejected:
            rejected.append("background-leakage")
            reasons.append("opaque subject does not block background energy")
    if not rejected:
        reasons.append("layering and energy retained")
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"composite_energy={format(composite, '.12g')}"],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
