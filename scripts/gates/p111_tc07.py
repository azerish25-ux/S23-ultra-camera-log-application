"""TC-P111-07 Bokeh ordering and leakage.

Host fixture. Uniform background blur without a coverage model is rejected.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P111-07"
NAME = "Bokeh ordering and leakage"
INTERVENTION = "Render strong foreground defocus with bright lights behind an in-focus opaque subject."
EXPECTED = "Respect layering and normalized energy while declaring unavoidable missing-background approximations."
NEGATIVE = "Uniform background blur with no foreground coverage model must fail."
REPEAT = "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem."
NEGATIVE_TOKEN = "uniform-background-blur-without-coverage-model"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "model",
    "subjectCoverage",
    "subjectDefocus",
    "foregroundDefocus",
    "backgroundDefocus",
    "leakage",
    "energy",
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


def _text(value, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _number(value, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    number = float(value)
    _require(math.isfinite(number), f"{label} must be finite")
    return number


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    model = payload["model"]
    _require(model in {"uniform-background", "layered"}, "model is invalid")
    coverage = _number(payload["subjectCoverage"], "subjectCoverage")
    subject = _number(payload["subjectDefocus"], "subjectDefocus")
    foreground = _number(payload["foregroundDefocus"], "foregroundDefocus")
    background = _number(payload["backgroundDefocus"], "backgroundDefocus")
    leakage = _number(payload["leakage"], "leakage")
    energy = _number(payload["energy"], "energy")
    _require(0.0 <= coverage <= 1.0, "subjectCoverage must be inside [0, 1]")
    _require(subject >= 0.0 and foreground >= 0.0 and background >= 0.0, "defocus must be >= 0")
    _require(leakage >= 0.0, "leakage must be >= 0")
    _require(energy > 0.0, "energy must be > 0")
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"model={model} coverage={coverage} leakage={leakage} energy={energy}",
        f"defocus subject={subject} foreground={foreground} background={background}",
    ]
    rejected: list[str] = []
    if model == "uniform-background":
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    else:
        if subject > 1e-9:
            rejected.append("subject-not-in-focus")
            reasons.append("opaque subject was not held at the focus plane")
        if foreground <= 0.0 or background <= 0.0:
            rejected.append("missing-layer-defocus")
            reasons.append("foreground and background defocus must both be present")
        if coverage >= 1.0 and leakage > 0.0:
            rejected.append("bokeh-leakage-through-opaque-subject")
            reasons.append("background energy leaked through an opaque in-focus subject")
        if not math.isclose(energy, 1.0, rel_tol=0.0, abs_tol=1e-6):
            rejected.append("energy-not-normalized")
            reasons.append("bokeh energy was not normalized")
        decision = "rejected" if rejected else "recorded"
        if decision == "recorded":
            reasons.append("layered bokeh respected coverage and normalized energy")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"energy:{energy}", f"leakage:{leakage}"],
        "openQuestions": [
            "physical S23 capture was not run",
            "unavoidable missing-background approximations remain declared",
            REPEAT,
        ],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
