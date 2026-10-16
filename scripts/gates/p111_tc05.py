"""TC-P111-05 Mixed-pixel boundaries.

Host fixture. A dilated binary mask cannot stand in for partial coverage.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P111-05"
NAME = "Mixed-pixel boundaries"
INTERVENTION = "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds."
EXPECTED = "Preserve plausible partial coverage and bound temporal halos under the selected safe settings."
NEGATIVE = "A dilated binary person mask must not pass demanding boundary quality by itself."
REPEAT = "Repeat backlighting, crossing subjects, and different foreground-background contrast."
NEGATIVE_TOKEN = "dilated-binary-person-mask"
PAYLOAD_KEYS = ("evidenceId", "repeat", "mask", "coverage", "haloRadius", "haloLimit")
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
    mask = payload["mask"]
    _require(mask in {"dilated-binary", "partial-coverage"}, "mask is invalid")
    coverage_in = payload["coverage"]
    _require(isinstance(coverage_in, list) and len(coverage_in) >= 2, "coverage must contain at least 2 samples")
    coverage = []
    for index, sample in enumerate(coverage_in):
        value = _number(sample, f"coverage {index}")
        _require(0.0 <= value <= 1.0, "coverage must be inside [0, 1]")
        coverage.append(value)
    halo_radius = _number(payload["haloRadius"], "haloRadius")
    halo_limit = _number(payload["haloLimit"], "haloLimit")
    _require(halo_radius >= 0.0, "haloRadius must be >= 0")
    _require(halo_limit > 0.0, "haloLimit must be > 0")
    fractional = [value for value in coverage if 0.0 < value < 1.0]
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"mask={mask} fractional={len(fractional)} halo_radius={halo_radius} halo_limit={halo_limit}",
    ]
    rejected: list[str] = []
    if mask == "dilated-binary":
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif not fractional:
        decision = "rejected"
        rejected.append("binary-coverage-not-partial")
        reasons.append("partial coverage was only 0 or 1")
    elif halo_radius > halo_limit:
        decision = "rejected"
        rejected.append("temporal-halo-exceeds-bound")
        reasons.append("temporal halo exceeded the selected safe bound")
    else:
        decision = "recorded"
        reasons.append("partial coverage preserved inside the halo bound")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"fractional:{len(fractional)}", f"halo_radius:{halo_radius}"],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
