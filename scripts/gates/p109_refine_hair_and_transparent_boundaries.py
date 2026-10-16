#!/usr/bin/env python3
"""P109 Refine hair and transparent boundaries.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P109-01 through TC-P109-08 modules.

Band rule: pixels with confidence < hair_threshold, or whose class is hair,
transparent, or glass, are seeds. Every sample within ``band`` indexes of a
seed is an unknown band, not a hard 0/1 matte. Unknown-band samples must not
be replaced by the foreground colour and then called opaque. Coverage is the
fraction of those seeds that remain unknown; a fraction below the declared
minimum is rejected. inpaint_glass true invents colour behind glass and is
rejected.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P109"
GOAL = "Improve mixed pixels without reducing the problem to a hard person mask."
METHOD = (
    "Use edge-aware upsampling and optional matting with temporal constraints. "
    "Represent partial coverage where justified and separate confidence from opacity. "
    "Evaluate hair, glasses, smoke, and motion-blurred edges; avoid facial smoothing "
    "as a substitute for segmentation accuracy."
)
FIXTURE = "Backlit hair moving against detailed foliage and transparent glasses crossing the face boundary."
ORACLE = "The renderer avoids conspicuous sharp cutouts and unstable halos under normal playback."
MUTANT = "Dilate a binary person mask and blur everything outside it uniformly."
DELIVERABLE = "Boundary refinement module and mixed-pixel corpus results"
BAND_RULE = (
    "pixels with confidence < hair_threshold or class in {hair, transparent, glass} "
    "become an unknown band of radius band samples, not a hard 0/1 matte"
)

MIXED_CLASSES = frozenset({"hair", "transparent", "glass"})
HARD_MATTE_CLASSES = frozenset({"hair", "transparent"})

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "hair_threshold",
    "band",
    "minimum_unknown_coverage",
    "inpaint_glass",
    "foreground_colour",
    "samples",
    "applyMutant",
}
SAMPLE_KEYS = {"confidence", "class", "matte", "colour", "called_opaque"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, message: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), message)
    number = float(value)
    require(math.isfinite(number), message)
    return number


def _unit(value: object, message: str) -> float:
    number = _number(value, message)
    require(0.0 <= number <= 1.0, message)
    return number


def _text(value: object, message: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), message)
    return value


def _matte_value(value: object, message: str) -> float | str:
    if value == "unknown":
        return "unknown"
    number = _number(value, message)
    require(0.0 <= number <= 1.0, message)
    return number


def is_hard_matte(value: object) -> bool:
    if value == "unknown" or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return float(value) == 0.0 or float(value) == 1.0
    return False


def is_seed(sample: dict, hair_threshold: float) -> bool:
    """Low-confidence boundary sample, or a hair, transparent, or glass sample."""
    return float(sample["confidence"]) < hair_threshold or sample["class"] in MIXED_CLASSES


def unknown_indexes(samples: list[dict], hair_threshold: float, band: int) -> tuple[list[int], list[int]]:
    """Return seed indexes and the inclusive radius-``band`` unknown band.

    Distance is the absolute difference of sample indexes. A seed at ``i`` marks
    every sample ``j`` with ``abs(j - i) <= band`` unknown.
    """
    seeds = [index for index, sample in enumerate(samples) if is_seed(sample, hair_threshold)]
    unknown: set[int] = set()
    last = len(samples)
    for seed in seeds:
        start = max(0, seed - band)
        stop = min(last, seed + band + 1)
        unknown.update(range(start, stop))
    return seeds, sorted(unknown)


def remains_unknown(sample: dict) -> bool:
    """True when a qualifying sample was not resolved to an opaque colour."""
    if sample["called_opaque"] is True:
        return False
    matte = sample["matte"]
    if matte == "unknown":
        return True
    if isinstance(matte, (int, float)) and not isinstance(matte, bool):
        return 0.0 < float(matte) < 1.0
    return False


def unknown_coverage(samples: list[dict], seeds: list[int]) -> float:
    """Fraction of low-confidence boundary samples that remain unknown.

    The denominator is the seed set: confidence < hair_threshold or class in
    {hair, transparent, glass}. No seeds yields coverage 1.
    """
    if not seeds:
        return 1.0
    kept = sum(1 for index in seeds if remains_unknown(samples[index]))
    return kept / len(seeds)


def _validate_sample(sample: object, index: int) -> dict:
    require(isinstance(sample, dict), f"sample {index} must be an object")
    missing = SAMPLE_KEYS - set(sample)
    extra = set(sample) - SAMPLE_KEYS
    require(not missing, f"sample {index} missing fields: " + ", ".join(sorted(missing)))
    require(not extra, f"sample {index} has unexpected fields: " + ", ".join(sorted(extra)))
    _unit(sample["confidence"], f"sample {index} confidence must be in [0, 1]")
    _text(sample["class"], f"sample {index} class must be a non-empty string")
    _matte_value(sample["matte"], f"sample {index} matte must be unknown or in [0, 1]")
    _text(sample["colour"], f"sample {index} colour must be a non-empty string")
    require(type(sample["called_opaque"]) is bool, f"sample {index} called_opaque must be a bool")
    return sample


def validate_document(document: dict) -> dict[str, Any]:
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1 and type(document["schemaVersion"]) is int, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _text(document["evidenceId"], "evidenceId must be a non-empty string")
    claim = _text(document["claim"], "claim must be a non-empty string")
    hair_threshold = _unit(document["hair_threshold"], "hair_threshold must be in [0, 1]")
    band = document["band"]
    require(type(band) is int and band >= 0, "band must be a non-negative int")
    minimum = _unit(document["minimum_unknown_coverage"], "minimum_unknown_coverage must be in [0, 1]")
    require(type(document["inpaint_glass"]) is bool, "inpaint_glass must be a bool")
    foreground = _text(document["foreground_colour"], "foreground_colour must be a non-empty string")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    samples = document["samples"]
    require(isinstance(samples, list) and len(samples) >= 1, "samples must be a non-empty list")
    checked = [_validate_sample(sample, index) for index, sample in enumerate(samples)]
    return {
        "evidence": evidence,
        "claim": claim,
        "hair_threshold": hair_threshold,
        "band": band,
        "minimum": minimum,
        "inpaint_glass": document["inpaint_glass"],
        "foreground_colour": foreground,
        "samples": checked,
        "applyMutant": document["applyMutant"],
    }


def refine(
    samples: list[dict],
    hair_threshold: float,
    band: int,
    foreground_colour: str | None = None,
) -> list[dict]:
    """Copy samples and mark the unknown band without inventing a hard matte.

    Band samples become matte ``unknown`` and are not called opaque. Colour is
    left unchanged, including glass: this function does not inpaint a colour
    behind glass and does not paint the band with ``foreground_colour``.
    """
    require(isinstance(samples, list) and samples, "samples must be a non-empty list")
    hair_threshold = _unit(hair_threshold, "hair_threshold must be in [0, 1]")
    require(type(band) is int and band >= 0, "band must be a non-negative int")
    checked = [_validate_sample(sample, index) for index, sample in enumerate(samples)]
    _seeds, unknown = unknown_indexes(checked, hair_threshold, band)
    unknown_set = set(unknown)
    refined: list[dict] = []
    for index, sample in enumerate(checked):
        item = {
            "confidence": sample["confidence"],
            "class": sample["class"],
            "matte": sample["matte"],
            "colour": sample["colour"],
            "called_opaque": sample["called_opaque"],
        }
        if index in unknown_set:
            item["matte"] = "unknown"
            item["called_opaque"] = False
            if foreground_colour is not None and item["colour"] == foreground_colour:
                # Keep the observed colour only if it was already there; never
                # promote it to an opaque foreground claim.
                item["called_opaque"] = False
        refined.append(item)
    return refined


def boundary_findings(parsed: dict[str, Any]) -> tuple[list[str], list[str], list[int], list[int], float]:
    """Return rejection claims, detail reasons, seeds, unknown indexes, coverage."""
    samples = parsed["samples"]
    seeds, unknown = unknown_indexes(samples, parsed["hair_threshold"], parsed["band"])
    coverage = unknown_coverage(samples, seeds)
    unknown_set = set(unknown)
    claims: list[str] = []
    details: list[str] = []
    if parsed["inpaint_glass"]:
        claims.append("inpaint_glass")
        details.append("inpaint_glass invents colour behind glass")
    if parsed["applyMutant"]:
        claims.append(MUTANT)
        details.append("mutant rejected: " + MUTANT)
    hard_labels = [sample for sample in samples if sample["class"] in HARD_MATTE_CLASSES]
    if hard_labels and all(is_hard_matte(sample["matte"]) for sample in hard_labels):
        claims.append("hard-matte-on-hair-or-transparent")
        details.append("hard matte of only 0 or 1 on hair/transparent labels")
    hard_band = [index for index in unknown if is_hard_matte(samples[index]["matte"])]
    if hard_band:
        claims.append("unknown-band-hard-matte")
        details.append(
            "unknown band must not be a hard 0/1 matte at indexes "
            + ",".join(str(index) for index in hard_band)
        )
    painted = [
        index
        for index in unknown
        if samples[index]["colour"] == parsed["foreground_colour"] and samples[index]["called_opaque"] is True
    ]
    if painted:
        claims.append("unknown-band-replaced-by-foreground-and-called-opaque")
        details.append(
            "unknown band samples replaced by the foreground colour and called opaque at indexes "
            + ",".join(str(index) for index in painted)
        )
    if coverage < parsed["minimum"]:
        claims.append("unknown-coverage-below-minimum")
        details.append(
            f"unknown coverage {coverage:.6f} is below declared minimum {parsed['minimum']:.6f}"
        )
    return claims, details, seeds, unknown, coverage


def _result(
    evidence: str,
    claim: str,
    claims: list[str],
    details: list[str],
    seeds: list[int],
    unknown: list[int],
    coverage: float,
    minimum: float,
    band: int,
) -> dict[str, Any]:
    decision = "rejected" if claims else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    band_text = ",".join(str(index) for index in unknown) if unknown else "none"
    seed_text = ",".join(str(index) for index in seeds) if seeds else "none"
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "band rule: " + BAND_RULE,
        f"seeds {seed_text}",
        f"unknown-band {band_text}",
        f"band-radius {band}",
        f"unknown-coverage {coverage:.6f}",
        f"declared-minimum {minimum:.6f}",
    ]
    if decision == "rejected":
        reasons.extend(details)
    else:
        reasons.append("unknown band retained; partial coverage was not reduced to a hard person mask")
        reasons.append("method: " + METHOD)
        reasons.append("evidence retained for " + evidence)
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": claims,
        "preservedResults": [evidence, claim],
        "openQuestions": [
            "physical S23 capture was not run",
            "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
        ],
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Judge a boundary-refinement document. Never qualifies the host fixture."""
    parsed = validate_document(document)
    claims, details, seeds, unknown, coverage = boundary_findings(parsed)
    return _result(
        parsed["evidence"],
        parsed["claim"],
        claims,
        details,
        seeds,
        unknown,
        coverage,
        parsed["minimum"],
        parsed["band"],
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Same host contract as ``assess`` for callers that ask to evaluate."""
    return assess(payload)
