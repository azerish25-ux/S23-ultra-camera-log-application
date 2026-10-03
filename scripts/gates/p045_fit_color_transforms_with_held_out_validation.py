#!/usr/bin/env python3
"""P045 held-out color-transform fitting.

Linearized chart measurements are fit against independently specified targets.
Training patches, held-out patches, and natural scenes stay separate. Weighting
and a Frobenius conditioning check are part of the report. A low training error
does not hide a large held-out saturated-blue error under a second light.

The deliberate mutant — validating a fit only against the patches used to
estimate it — is rejected. Training-only acceptance is never a profile.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P045-01 through TC-P045-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P045"
CASE_ID = "P045"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-held-out-color-fit-fixture"
METHOD = (
    "Use linearized source measurements and independently specified target data. "
    "Fit with documented weighting and conditioning checks. Separate training patches, "
    "held-out patches, and natural scenes. Report neutral preservation and error "
    "distributions under the specified illuminant."
)
FIXTURE = (
    "A chart fit with low training error but large held-out saturated-blue error "
    "under a second light source."
)
ORACLE = (
    "The profile remains limited to its validated conditions and the report exposes "
    "the held-out failure."
)
MUTANT = "Validate a fit only against the same patches used to estimate it."
WEIGHTING = "inverse-variance"
CONDITION_METRIC = "frobenius"
CONDITION_THRESHOLD = "1000"
TRAIN_LIMIT = Decimal("0.02")
HELD_OUT_FAIL = Decimal("0.15")
NEUTRAL_LIMIT = Decimal("0.01")
MUTANT_TEST = "training-patches-only"
INDEPENDENT = "held-out"
SOLE_TESTS = {INDEPENDENT, MUTANT_TEST}
HOST_LIMIT = "host fixture does not qualify a physical S23 or a measured camera profile"
MUTANT_ACCEPT = "training_validated"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}")
SCENE_ROLES = {"skin", "saturated-fabric", "foliage", "narrow-band"}
HELDOUT_ROLES = {"saturated-blue"}

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "weighting",
    "conditioning",
    "illuminant",
    "neutralPatchId",
    "training",
    "heldOut",
    "naturalScenes",
    "matrix",
}
CONDITION_KEYS = {"metric", "threshold"}
PATCH_KEYS = {"id", "source", "target", "weight"}
HELDOUT_KEYS = {"id", "illuminant", "source", "target", "role"}
SCENE_KEYS = {"id", "illuminant", "role"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", MUTANT_ACCEPT}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def canonical(value: Decimal) -> str:
    """Render a Decimal without exponent notation or trailing zeros."""
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _decimal(value: object, label: str, signed: bool = False) -> str:
    pattern = SIGNED if signed else DECIMAL
    require(isinstance(value, str) and pattern.fullmatch(value) is not None, label + " must be a canonical decimal string")
    require(value not in {"-0"}, label + " must not be negative zero")
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _rgb(value: object, label: str) -> list[str]:
    require(type(value) is list and len(value) == 3, label + " must be three components")
    return [_decimal(item, label) for item in value]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P045 must not decide qualified, allowed, or training_validated")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _det(m: list[Decimal]) -> Decimal:
    a, b, c, d, e, f, g, h, i = m
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def invert_matrix(matrix: list[str]) -> list[Decimal]:
    """Invert a row-major 3x3. Raises ValueError when the determinant is zero."""
    m = [Decimal(item) for item in matrix]
    det = _det(m)
    if det == 0:
        raise ValueError("singular matrix")
    a, b, c, d, e, f, g, h, i = m
    return [
        (e * i - f * h) / det,
        (c * h - b * i) / det,
        (b * f - c * e) / det,
        (f * g - d * i) / det,
        (a * i - c * g) / det,
        (c * d - a * f) / det,
        (d * h - e * g) / det,
        (b * g - a * h) / det,
        (a * e - b * d) / det,
    ]


def frobenius_condition(matrix: list[str]) -> Decimal:
    """Return ||A||_F * ||A^-1||_F, computed as sqrt of the product of squares."""
    inverse = invert_matrix(matrix)
    sum_a = sum((Decimal(item) ** 2 for item in matrix), Decimal(0))
    sum_i = sum((item ** 2 for item in inverse), Decimal(0))
    return (sum_a * sum_i).sqrt()


def _apply(matrix: list[str], rgb: list[str]) -> tuple[Decimal, Decimal, Decimal]:
    m = [Decimal(item) for item in matrix]
    x, y, z = (Decimal(item) for item in rgb)
    return (
        m[0] * x + m[1] * y + m[2] * z,
        m[3] * x + m[4] * y + m[5] * z,
        m[6] * x + m[7] * y + m[8] * z,
    )


def _distance(left: tuple[Decimal, Decimal, Decimal], right: list[str]) -> Decimal:
    total = Decimal(0)
    for item, target in zip(left, right):
        delta = item - Decimal(target)
        total += delta * delta
    return total.sqrt()


def _patch(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, PATCH_KEYS, f"training {index}")
    ident = _token(item["id"], f"training {index} id")
    require(ident not in seen, "duplicate training id: " + ident)
    seen.add(ident)
    _rgb(item["source"], f"training {index} source")
    _rgb(item["target"], f"training {index} target")
    weight = _decimal(item["weight"], f"training {index} weight")
    require(Decimal(weight) > 0, f"training {index} weight must be positive")
    return item


def _held_out(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, HELDOUT_KEYS, f"heldOut {index}")
    ident = _token(item["id"], f"heldOut {index} id")
    require(ident not in seen, "duplicate held-out id: " + ident)
    seen.add(ident)
    _token(item["illuminant"], f"heldOut {index} illuminant")
    _rgb(item["source"], f"heldOut {index} source")
    _rgb(item["target"], f"heldOut {index} target")
    role = _token(item["role"], f"heldOut {index} role")
    require(role in HELDOUT_ROLES, f"heldOut {index} role must be saturated-blue")
    return item


def _scene(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, SCENE_KEYS, f"natural scene {index}")
    ident = _token(item["id"], f"natural scene {index} id")
    require(ident not in seen, "duplicate scene id: " + ident)
    seen.add(ident)
    _token(item["illuminant"], f"natural scene {index} illuminant")
    role = item["role"]
    require(role in SCENE_ROLES, f"natural scene {index} role is unsupported")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P045 held-out color-fit fixture."""
    exact_keys(document, DOCUMENT_KEYS, "color fit")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P045")
    require(document["mapId"] == MAP_ID, "mapId must be s23-held-out-color-fit-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "color fit needs the P045 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["weighting"] == WEIGHTING, "weighting must be inverse-variance")
    conditioning = exact_keys(document["conditioning"], CONDITION_KEYS, "conditioning")
    require(conditioning["metric"] == CONDITION_METRIC, "conditioning metric must be frobenius")
    require(conditioning["threshold"] == CONDITION_THRESHOLD, "conditioning threshold drifted")
    _token(document["illuminant"], "illuminant")
    neutral_id = _token(document["neutralPatchId"], "neutralPatchId")
    training = document["training"]
    require(type(training) is list and training, "training must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(training):
        _patch(item, index, seen)
    require(neutral_id in seen, "neutralPatchId must name a training patch")
    held = document["heldOut"]
    require(type(held) is list, "heldOut must be a list")
    seen_held: set[str] = set()
    for index, item in enumerate(held):
        _held_out(item, index, seen_held)
    scenes = document["naturalScenes"]
    require(type(scenes) is list and scenes, "naturalScenes must be a non-empty list")
    seen_scenes: set[str] = set()
    for index, item in enumerate(scenes):
        _scene(item, index, seen_scenes)
    matrix = document["matrix"]
    require(type(matrix) is list and len(matrix) == 9, "matrix must be nine coefficients")
    for item in matrix:
        _decimal(item, "matrix coefficient", signed=True)


def _neutral_status(document: dict, matrix: list[str] | None) -> str:
    patch = next(item for item in document["training"] if item["id"] == document["neutralPatchId"])
    if matrix is None:
        return "unavailable"
    mapped = _apply(matrix, patch["source"])
    delta = max(abs(item - Decimal(target)) for item, target in zip(mapped, patch["target"]))
    if delta <= NEUTRAL_LIMIT:
        return "preserved"
    return "shifted"


def _stats(document: dict) -> dict[str, Any]:
    matrix = document["matrix"]
    try:
        condition = frobenius_condition(matrix)
        invertible = True
    except ValueError:
        condition = None
        invertible = False
    training_errors: list[Decimal] = []
    weights: list[Decimal] = []
    if invertible:
        for patch in document["training"]:
            training_errors.append(_distance(_apply(matrix, patch["source"]), patch["target"]))
            weights.append(Decimal(patch["weight"]))
        weight_sum = sum(weights, Decimal(0))
        accum = sum((weight * error * error for weight, error in zip(weights, training_errors)), Decimal(0))
        training_rmse = (accum / weight_sum).sqrt()
    else:
        training_rmse = None
    held_errors: list[Decimal | None] = []
    if invertible:
        for patch in document["heldOut"]:
            held_errors.append(_distance(_apply(matrix, patch["source"]), patch["target"]))
    else:
        held_errors = [None for _ in document["heldOut"]]
    saturated = next((item for item in document["heldOut"] if item["id"] == "saturated-blue"), None)
    saturated_error = None
    if saturated is not None and invertible:
        index = document["heldOut"].index(saturated)
        saturated_error = held_errors[index]
    return {
        "invertible": invertible,
        "condition": condition,
        "training_errors": training_errors,
        "training_rmse": training_rmse,
        "held_errors": held_errors,
        "saturated": saturated,
        "saturated_error": saturated_error,
        "neutral": _neutral_status(document, matrix if invertible else None),
    }


def training_rmse(document: dict) -> Decimal:
    """Weighted training RMSE. Raises ValueError when the matrix is singular."""
    validate_document(document)
    stats = _stats(document)
    require(stats["training_rmse"] is not None, "training RMSE is unavailable for a singular matrix")
    return stats["training_rmse"]


def held_out_error(document: dict, patch_id: str) -> Decimal:
    """Euclidean error of one held-out patch after the matrix is applied."""
    validate_document(document)
    stats = _stats(document)
    require(stats["invertible"], "held-out error is unavailable for a singular matrix")
    for patch, error in zip(document["heldOut"], stats["held_errors"]):
        if patch["id"] == patch_id:
            return error
    raise ValueError("unknown held-out patch")


def training_only_would_accept(document: dict) -> bool:
    """True when the mutant would accept the fit from training error alone.

    A low training RMSE is not held-out validation. ``assess`` must not turn
    this predicate into ``training_validated``, ``qualified``, or ``allowed``.
    """
    validate_document(document)
    stats = _stats(document)
    if not stats["invertible"] or stats["training_rmse"] is None:
        return False
    limit = Decimal(document["conditioning"]["threshold"])
    if stats["condition"] >= limit:
        return False
    return stats["training_rmse"] <= TRAIN_LIMIT


def _preserved(document: dict, stats: dict[str, Any]) -> list[str]:
    preserved: list[str] = []
    if stats["invertible"]:
        for patch, error in zip(document["training"], stats["training_errors"]):
            preserved.append(f"training:{patch['id']}:w={patch['weight']}:e={canonical(error)}")
        for patch, error in zip(document["heldOut"], stats["held_errors"]):
            preserved.append(
                f"held-out:{patch['id']}:{patch['illuminant']}:e={canonical(error)}"
            )
        preserved.append(f"training-rmse:{canonical(stats['training_rmse'])}")
        preserved.append(f"conditioning:{canonical(stats['condition'])}")
    else:
        for patch in document["training"]:
            preserved.append(f"training:{patch['id']}:w={patch['weight']}:e=unavailable")
        for patch in document["heldOut"]:
            preserved.append(f"held-out:{patch['id']}:{patch['illuminant']}:e=unavailable")
        preserved.append("training-rmse:unavailable")
        preserved.append("conditioning:singular")
    for scene in document["naturalScenes"]:
        preserved.append(f"scene:{scene['id']}:{scene['illuminant']}:{scene['role']}")
    preserved.append(f"neutral:{document['neutralPatchId']}:{stats['neutral']}")
    preserved.append("weighting:" + document["weighting"])
    preserved.append("matrix:" + ",".join(document["matrix"]))
    preserved.append("fit-illuminant:" + document["illuminant"])
    return preserved


def assess(document: dict, sole_test: str = INDEPENDENT) -> dict:
    """Limit the profile to validated conditions and expose held-out failure.

    sole_test ``training-patches-only`` is the mutant. It is rejected even when
    training RMSE is inside the training limit. Held-out errors stay in
    preservedResults. The decision is never ``qualified``, ``allowed``, or
    ``training_validated``.
    """
    validate_document(document)
    require(sole_test in SOLE_TESTS, "sole_test must be held-out or training-patches-only")
    stats = _stats(document)
    preserved = _preserved(document, stats)
    questions = [
        "host fixture is not a physical S23 measurement",
        "natural scenes are not training patches and were not used to accept the fit",
    ]
    for scene in document["naturalScenes"]:
        questions.append(f"natural scene {scene['id']} ({scene['role']}) is outside the chart fit")
    reasons = [
        ORACLE,
        "weighting " + document["weighting"] + " applies only to training patches",
        "training patches, held-out patches, and natural scenes are reported separately",
    ]
    rejected: list[str] = []
    threshold = Decimal(document["conditioning"]["threshold"])
    if not stats["invertible"]:
        rejected.append("singular-matrix")
        reasons.append("the matrix is singular so inversion was rejected")
    elif stats["condition"] >= threshold:
        rejected.append("ill-conditioned")
        reasons.append(
            f"frobenius condition {canonical(stats['condition'])} is not below {document['conditioning']['threshold']}"
        )
    else:
        reasons.append(
            f"frobenius condition {canonical(stats['condition'])} is below {document['conditioning']['threshold']}"
        )
    if stats["training_rmse"] is None:
        reasons.append("training RMSE was not treated as a passing score")
    elif stats["training_rmse"] <= TRAIN_LIMIT:
        reasons.append(
            f"training rmse {canonical(stats['training_rmse'])} under {document['illuminant']} "
            f"is within {canonical(TRAIN_LIMIT)}"
        )
    else:
        rejected.append("training-error")
        reasons.append(
            f"training rmse {canonical(stats['training_rmse'])} exceeds {canonical(TRAIN_LIMIT)}"
        )
    if stats["neutral"] == "shifted":
        rejected.append("neutral-shift")
        reasons.append(f"neutral patch {document['neutralPatchId']} is not preserved")
    elif stats["neutral"] == "preserved":
        reasons.append(f"neutral patch {document['neutralPatchId']} is preserved")
    else:
        reasons.append("neutral preservation was not scored on a singular matrix")
    saturated = stats["saturated"]
    held_failed = False
    if saturated is None:
        questions.append("saturated-blue held-out patch is missing")
        reasons.append("held-out saturated-blue error was not dropped from the report")
    else:
        if stats["saturated_error"] is None:
            reasons.append("held-out saturated-blue error is unavailable because the matrix is singular")
        else:
            error = stats["saturated_error"]
            reasons.append(
                f"held-out saturated-blue error {canonical(error)} under {saturated['illuminant']}"
            )
            if error >= HELD_OUT_FAIL:
                held_failed = True
                rejected.append("held-out-saturated-blue")
                reasons.append(
                    f"held-out saturated-blue error {canonical(error)} exceeds {canonical(HELD_OUT_FAIL)}"
                )
            else:
                reasons.append("held-out saturated-blue error is inside the host failure threshold")
        second = saturated["illuminant"] != document["illuminant"]
        if second and held_failed:
            rejected.append("second-illuminant")
            reasons.append(
                f"second light {saturated['illuminant']} is outside fit illuminant {document['illuminant']}"
            )
            questions.append(
                f"profile limited to training illuminant {document['illuminant']}; "
                f"second light {saturated['illuminant']} is not supported"
            )
        elif not second:
            questions.append("held-out illuminant matches the fit illuminant")
    if sole_test == MUTANT_TEST:
        decision = "rejected"
        rejected.insert(0, "training-only-validation")
        reasons.append(MUTANT)
        reasons.append("low training error does not validate the fit")
        questions.append("training-only validation was rejected")
    elif (not stats["invertible"]) or ("ill-conditioned" in rejected) or ("training-error" in rejected):
        decision = "rejected"
    elif "neutral-shift" in rejected and not held_failed:
        decision = "rejected"
    elif saturated is None:
        decision = "withheld"
    elif held_failed:
        decision = "limited"
        reasons.append("the profile stays limited to its validated conditions")
    else:
        decision = "withheld"
        questions.append("held-out did not fail in this host fixture; the profile is still not qualified")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
