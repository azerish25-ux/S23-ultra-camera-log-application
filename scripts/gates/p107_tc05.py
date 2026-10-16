"""TC-P107-05 Mixed-pixel boundaries.

Host reference. Partial coverage is required. A dilated binary mask is not enough.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P107-05"
NAME = "Mixed-pixel boundaries"
INTERVENTION = "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds."
EXPECTED = "Preserve plausible partial coverage and bound temporal halos under the selected safe settings."
NEGATIVE = "A dilated binary person mask must not pass demanding boundary quality by itself."
REPEAT = "Repeat backlighting, crossing subjects, and different foreground-background contrast."
NEGATIVE_TOKEN = "dilated-binary-person-mask"
PAYLOAD_KEYS = ("evidenceId", "repeat", "coverage", "dilated_binary_mask_only", "halo_px", "halo_limit_px")
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
    _require(type(payload["dilated_binary_mask_only"]) is bool, "dilated_binary_mask_only must be a bool")
    coverage = payload["coverage"]
    _require(isinstance(coverage, list) and coverage, "coverage must be a non-empty list")
    values = [_number(item, f"coverage[{index}]") for index, item in enumerate(coverage)]
    for value in values:
        _require(0.0 <= value <= 1.0, "coverage must lie in [0, 1]")
    halo = _number(payload["halo_px"], "halo_px")
    limit = _number(payload["halo_limit_px"], "halo_limit_px")
    _require(halo >= 0.0 and limit >= 0.0, "halo lengths must be non-negative")
    partial = sum(1 for value in values if 0.0 < value < 1.0)
    fraction = partial / float(len(values))
    margin = limit - halo
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"partial_fraction={format(fraction, '.12g')}",
        f"halo_margin_px={format(margin, '.12g')}",
    ]
    rejected: list[str] = []
    if payload["dilated_binary_mask_only"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if margin < 0.0:
        rejected.append("temporal-halo-unbounded")
        reasons.append("temporal halo exceeds the selected safe bound")
    if fraction == 0.0:
        rejected.append("no-partial-coverage")
        reasons.append("binary coverage does not preserve mixed pixels")
    if not rejected:
        reasons.append("partial coverage retained inside the halo bound")
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"partial_fraction={format(fraction, '.12g')}"],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
