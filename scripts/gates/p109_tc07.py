"""TC-P109-07 Bokeh ordering and leakage.

Host fixture. Uniform background blur without a coverage model is rejected.
Kernel energy is checked, and glass is not inpainted.
A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P109-07"
NAME = "Bokeh ordering and leakage"
INTERVENTION = "Render strong foreground defocus with bright lights behind an in-focus opaque subject."
EXPECTED = "Respect layering and normalized energy while declaring unavoidable missing-background approximations."
NEGATIVE = "Uniform background blur with no foreground coverage model must fail."
REPEAT = "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem."
NEGATIVE_TOKEN = "uniform-background-blur-without-foreground-coverage"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "uniformBackgroundBlur",
    "foregroundCoverage",
    "kernelEnergy",
    "missingBackgroundDeclared",
    "inpaint_glass",
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


def _partial(value: object) -> bool:
    if value == "unknown":
        return True
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    return math.isfinite(number) and 0.0 < number < 1.0


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
    _require(type(payload["uniformBackgroundBlur"]) is bool, "uniformBackgroundBlur must be a bool")
    _require(type(payload["missingBackgroundDeclared"]) is bool, "missingBackgroundDeclared must be a bool")
    _require(type(payload["inpaint_glass"]) is bool, "inpaint_glass must be a bool")
    coverage = payload["foregroundCoverage"]
    energy = payload["kernelEnergy"]
    _require(isinstance(coverage, list) and len(coverage) >= 1, "foregroundCoverage must be a non-empty list")
    _require(isinstance(energy, list) and len(energy) >= 1, "kernelEnergy must be a non-empty list")
    weights: list[float] = []
    for index, item in enumerate(coverage):
        if item == "unknown":
            continue
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"coverage {index}")
        number = float(item)
        _require(math.isfinite(number) and 0.0 <= number <= 1.0, f"coverage {index}")
    for index, item in enumerate(energy):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"kernelEnergy {index}")
        number = float(item)
        _require(math.isfinite(number) and number >= 0.0, f"kernelEnergy {index}")
        weights.append(number)
    total = sum(weights)
    has_coverage_model = any(_partial(item) for item in coverage)
    claims: list[str] = []
    if payload["uniformBackgroundBlur"] and not has_coverage_model:
        claims.append(NEGATIVE_TOKEN)
    elif not has_coverage_model:
        claims.append("missing-foreground-coverage-model")
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-6):
        claims.append("kernel-energy-not-normalized")
    if payload["missingBackgroundDeclared"] is False:
        claims.append("missing-background-not-declared")
    if payload["inpaint_glass"] is True:
        claims.append("inpaint_glass")
    detail = f"kernel-energy {total:.6f}; coverage-model {has_coverage_model}"
    decision = "rejected" if claims else "recorded"
    return _finish(evidence, repeat, decision, claims, detail)
