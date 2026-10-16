#!/usr/bin/env python3
"""P107 Align relative depth scale and offset.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Relative depth is aligned to a reference by ordinary least
squares on the normal equations:

    depth_ref ≈ scale * depth_rel + offset

    scale = (n * Σ(x y) - Σx * Σy) / (n * Σ(x²) - (Σx)²)
    offset = (Σy - scale * Σx) / n
    RMSE = sqrt(Σ(scale * x + offset - y)² / n)

with x = depth_rel, y = depth_ref, and n >= 3 finite training pairs.
Hold-out pairs are scored with that scale and offset and are not entered
into the sums. This module does not execute TC-P107-01 through TC-P107-08.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P107"
WORKSTREAM = 14
DEPENDENCIES = ("P106",)
TITLE = "Align relative depth scale and offset"
GOAL = "Prevent arbitrary model normalization from becoming visible focus breathing."
METHOD = (
    "Estimate robust alignment only over valid, stable correspondences and use the model "
    "appropriate to its output semantics. Bound fits, reject ill-conditioned scenes, and "
    "retain confidence. Do not perform global min-max normalization independently on every frame."
)
FIXTURE = "A scene where a close object enters the frame while the background remains stationary."
ORACLE = "Background blur remains stable unless its actual geometry or selected focus changes."
MUTANT = "Renormalize each depth map using its current minimum and maximum."
DELIVERABLE = "Relative-depth alignment and focus-pumping tests"

MIN_PAIRS = 3
UNIT_SCALE_RMSE_TOLERANCE = 1e-6
SCALE_FAR_FROM_ONE = 1e-3
_ILL_CONDITIONED = 1e-12

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "aligned_unit",
    "reference_unit",
    "force_unit_scale",
    "holdout_in_fit",
    "pairs",
    "holdout",
    "foreground",
}
ALLOWED_KEYS = DOCUMENT_KEYS | {"tolerance", "caseId"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_PAIR_KEYS = {"id", "depth_rel", "depth_ref", "depthRel", "depthRef"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical(value: float) -> str:
    text = format(float(value), ".12g")
    if text in {"-0", "-0.0", "0.0"}:
        return "0"
    return text


def _evidence(value: object) -> str:
    require(
        isinstance(value, str) and value.strip() and value == value.strip(),
        "evidenceId must be a non-empty string",
    )
    return value


def _number(value: object, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    return float(value)


def _optional_id(value: object, label: str) -> str | None:
    if value is None:
        return None
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _one_pair(item: object, index: int, label: str) -> tuple[str | None, float, float]:
    if isinstance(item, (list, tuple)):
        require(len(item) in {2, 3}, f"{label}[{index}] must contain depth_rel and depth_ref")
        if len(item) == 3:
            ident = _optional_id(item[0], f"{label}[{index}].id")
            require(ident is not None, f"{label}[{index}].id must be a non-empty string")
            return ident, _number(item[1], f"{label}[{index}].depth_rel"), _number(item[2], f"{label}[{index}].depth_ref")
        return None, _number(item[0], f"{label}[{index}].depth_rel"), _number(item[1], f"{label}[{index}].depth_ref")
    require(isinstance(item, dict), f"{label}[{index}] must be an object")
    extra = set(item) - _PAIR_KEYS
    require(not extra, f"{label}[{index}] has unexpected fields: " + ", ".join(sorted(extra)))
    if "depth_rel" in item:
        x_raw = item["depth_rel"]
    elif "depthRel" in item:
        x_raw = item["depthRel"]
    else:
        raise ValueError(f"{label}[{index}] missing depth_rel")
    if "depth_ref" in item:
        y_raw = item["depth_ref"]
    elif "depthRef" in item:
        y_raw = item["depthRef"]
    else:
        raise ValueError(f"{label}[{index}] missing depth_ref")
    if "depth_rel" in item and "depthRel" in item:
        require(item["depth_rel"] == item["depthRel"], f"{label}[{index}] has conflicting depth_rel")
    if "depth_ref" in item and "depthRef" in item:
        require(item["depth_ref"] == item["depthRef"], f"{label}[{index}] has conflicting depth_ref")
    return _optional_id(item.get("id"), f"{label}[{index}].id"), _number(x_raw, f"{label}[{index}].depth_rel"), _number(
        y_raw, f"{label}[{index}].depth_ref"
    )


def _parse_pairs(items: object, label: str) -> list[tuple[str | None, float, float]]:
    require(isinstance(items, list), f"{label} must be a list")
    parsed: list[tuple[str | None, float, float]] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        ident, x_value, y_value = _one_pair(item, index, label)
        if ident is not None:
            require(ident not in seen, f"duplicate id in {label}: {ident}")
            seen.add(ident)
        parsed.append((ident, x_value, y_value))
    return parsed


def _is_relative(label: str) -> bool:
    return " ".join(label.strip().lower().replace("-", " ").replace("_", " ").split()) == "relative"


def _is_metric_metres(label: str) -> bool:
    text = " ".join(label.strip().lower().replace("-", " ").replace("_", " ").split())
    return text in {"metric metres", "metric meters", "metres", "meters"}


def _normal_equations(xs: list[float], ys: list[float]) -> tuple[float, float, float] | None:
    """Solve depth_ref ≈ scale * depth_rel + offset. None if the 2x2 system is singular."""
    n = float(len(xs))
    sx = sy = sxx = sxy = 0.0
    for x_value, y_value in zip(xs, ys):
        sx += x_value
        sy += y_value
        sxx += x_value * x_value
        sxy += x_value * y_value
    denom = n * sxx - sx * sx
    if abs(denom) <= _ILL_CONDITIONED * max(1.0, abs(n * sxx), abs(sx * sx)):
        return None
    scale = (n * sxy - sx * sy) / denom
    offset = (sy - scale * sx) / n
    if not math.isfinite(scale) or not math.isfinite(offset):
        return None
    return scale, offset, _rmse(scale, offset, xs, ys)


def _rmse(scale: float, offset: float, xs: list[float], ys: list[float]) -> float:
    error = 0.0
    for x_value, y_value in zip(xs, ys):
        residual = scale * x_value + offset - y_value
        error += residual * residual
    return math.sqrt(error / float(len(xs)))


def _unit_scale_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Constant-bias model: depth_ref ≈ 1 * depth_rel + offset."""
    n = float(len(xs))
    offset = sum(y_value - x_value for x_value, y_value in zip(xs, ys)) / n
    return offset, _rmse(1.0, offset, xs, ys)


def fit_relative_depth(pairs: list) -> dict[str, float]:
    """Return scale, offset, and RMSE for depth_ref ≈ scale * depth_rel + offset.

    Raises ValueError when fewer than 3 pairs are supplied, a value is non-finite,
    or the normal equations are singular. A negative scale is returned so the
    caller can see the reversed fit; evaluate() rejects that decision.
    """
    parsed = _parse_pairs(pairs, "pairs")
    require(len(parsed) >= MIN_PAIRS, "at least 3 finite pairs are required")
    for _, x_value, y_value in parsed:
        require(math.isfinite(x_value) and math.isfinite(y_value), "non-finite depth")
    fit = _normal_equations([item[1] for item in parsed], [item[2] for item in parsed])
    require(fit is not None, "ill-conditioned depth fit")
    scale, offset, rmse = fit
    return {"scale": scale, "offset": offset, "rmse": rmse}


def _result(
    case_id: str,
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(any("physical S23" in item and "not run" in item for item in questions), "physical S23 note missing")
    require(bool(reasons), "reasons must be non-empty")
    return result


def evaluate(payload: dict) -> dict[str, Any]:
    """Fit relative depth and accept only a bounded, non-reversed, non-leaking alignment."""
    require(isinstance(payload, dict), "payload must be an object")
    extra = set(payload) - ALLOWED_KEYS
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    require("evidenceId" in payload, "payload missing evidenceId")
    require("pairs" in payload, "payload missing pairs")
    evidence = _evidence(payload["evidenceId"])
    claim = payload.get("claim")
    if claim is not None:
        require(isinstance(claim, str) and claim.strip() and claim == claim.strip(), "claim must be a non-empty string")
    case_id = payload.get("caseId", PHASE)
    require(isinstance(case_id, str) and case_id.strip() and case_id == case_id.strip(), "caseId must be a non-empty string")
    aligned = payload.get("aligned_unit", "relative")
    reference = payload.get("reference_unit", "relative")
    require(isinstance(aligned, str) and aligned.strip(), "aligned_unit must be a non-empty string")
    require(isinstance(reference, str) and reference.strip(), "reference_unit must be a non-empty string")
    force_unit = payload.get("force_unit_scale", False)
    holdout_in_fit = payload.get("holdout_in_fit", False)
    apply_mutant = payload.get("applyMutant", False)
    require(type(force_unit) is bool, "force_unit_scale must be a bool")
    require(type(holdout_in_fit) is bool, "holdout_in_fit must be a bool")
    require(type(apply_mutant) is bool, "applyMutant must be a bool")
    tolerance = payload.get("tolerance", UNIT_SCALE_RMSE_TOLERANCE)
    require(isinstance(tolerance, (int, float)) and not isinstance(tolerance, bool), "tolerance must be a number")
    tolerance_value = float(tolerance)
    require(math.isfinite(tolerance_value) and tolerance_value >= 0.0, "tolerance must be finite and non-negative")

    train = _parse_pairs(payload["pairs"], "pairs")
    holdout = _parse_pairs(payload.get("holdout", []), "holdout")
    foreground = _parse_pairs(payload.get("foreground", []), "foreground")
    if holdout and any(ident is None for ident, _, _ in train + holdout):
        raise ValueError("ids are required when hold-out pairs are provided")
    if foreground and any(ident is None for ident, _, _ in train + foreground):
        raise ValueError("ids are required when foreground pairs are provided")

    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
    ]
    rejected: list[str] = []
    questions = [
        "physical S23 was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    if _is_metric_metres(aligned) and _is_relative(reference):
        rejected.append("metric-metres-on-relative-reference")
        reasons.append("aligned values labeled metric metres but reference unit is relative")
    if apply_mutant:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)

    train_ids = {ident for ident, _, _ in train if ident is not None}
    hold_ids = {ident for ident, _, _ in holdout if ident is not None}
    foreground_ids = {ident for ident, _, _ in foreground if ident is not None}
    overlap = train_ids & hold_ids
    unstable = train_ids & foreground_ids
    if holdout_in_fit or overlap:
        rejected.append("holdout-leakage")
        reasons.append("hold-out pairs must be scored separately and not used in the fit")
        if overlap:
            reasons.append("overlapping ids: " + ",".join(sorted(overlap)))
    if unstable:
        rejected.append("unstable-correspondence")
        reasons.append("foreground correspondences are not stable background pairs")

    non_finite = any(
        not math.isfinite(x_value) or not math.isfinite(y_value)
        for _, x_value, y_value in train + holdout + foreground
    )
    scale: float | None = None
    offset: float | None = None
    rmse: float | None = None
    hold_rmse: float | None = None
    if non_finite:
        rejected.append("non-finite-depth")
        reasons.append("non-finite depth rejected")
    elif len(train) < MIN_PAIRS:
        rejected.append("fewer-than-3-points")
        reasons.append(f"need at least {MIN_PAIRS} finite pairs")
    else:
        xs = [item[1] for item in train]
        ys = [item[2] for item in train]
        fit = _normal_equations(xs, ys)
        if fit is None:
            rejected.append("ill-conditioned")
            reasons.append("normal equations are ill-conditioned")
        else:
            scale, offset, rmse = fit
            reasons.append(
                "normal equations on %d finite pairs: depth_ref = %s * depth_rel + %s; rmse %s"
                % (len(xs), canonical(scale), canonical(offset), canonical(rmse))
            )
            if scale < 0.0:
                rejected.append("negative-scale")
                rejected.append("depth-reversed")
                reasons.append("negative scale reverses depth")
            leaked = bool(holdout_in_fit or overlap)
            if holdout and not leaked and all(math.isfinite(x_value) and math.isfinite(y_value) for _, x_value, y_value in holdout):
                hold_rmse = _rmse(scale, offset, [item[1] for item in holdout], [item[2] for item in holdout])
                reasons.append("hold-out rmse %s scored separately from the fit" % canonical(hold_rmse))
            if foreground and not unstable:
                reasons.append("foreground excluded from the normal equations")
            if force_unit:
                _unit_offset, unit_rmse = _unit_scale_fit(xs, ys)
                reasons.append("unit-scale rmse %s tolerance %s" % (canonical(unit_rmse), canonical(tolerance_value)))
                if abs(scale - 1.0) > SCALE_FAR_FROM_ONE and unit_rmse > tolerance_value:
                    rejected.append("constant-bias-fix")
                    reasons.append("constant bias fix rejected: true scale is far from 1")

    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("confidence retained as training rmse " + canonical(rmse if rmse is not None else 0.0))
    preserved = [evidence]
    if isinstance(claim, str):
        preserved.append(claim)
    if scale is not None and offset is not None and rmse is not None:
        preserved.append("scale:" + canonical(scale))
        preserved.append("offset:" + canonical(offset))
        preserved.append("rmse:" + canonical(rmse))
    if hold_rmse is not None:
        preserved.append("holdout-rmse:" + canonical(hold_rmse))
    return _result(case_id, decision, reasons, rejected, preserved, questions, evidence)


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle to a host alignment fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    result = evaluate(document)
    require(result["caseId"] == PHASE, "assess caseId must be the phase id")
    return result
