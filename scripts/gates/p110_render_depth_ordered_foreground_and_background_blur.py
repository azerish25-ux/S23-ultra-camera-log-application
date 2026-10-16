#!/usr/bin/env python3
"""P110 Render depth-ordered foreground and background blur.

Host fixture only. This module does not probe a device and does not qualify a
physical S23. It is an occlusion-aware 1D reference, not a uniform Gaussian.

Blur rule
---------
Larger depth is farther. For a known depth the gather radius is
``DEFOCUS_RADIUS_SCALE * abs(depth - focus)``. Samples within
``FOCUS_EPSILON`` of the focus plane are sharp: neighbour mix weight is 0.
Background samples mix only with background samples. Foreground samples mix
only with foreground samples and must not contribute to a background output
bin. Unknown depth stays unknown; it is not blurred as if it were far.
A uniform Gaussian applied to every sample regardless of depth, when labelled
``optical_bokeh``, is rejected. Kernels are renormalized on in-strip admitted
samples. Missing background behind an opaque focus sample is not invented.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P110"
TITLE = "Render depth-ordered foreground and background blur"
GOAL = "Implement an occlusion-aware lens renderer rather than a single per-pixel Gaussian blur."
METHOD = (
    "Start with layered or scatter-gather reference rendering using signed defocus, "
    "coverage, and normalized kernels. Test foreground spread, background leakage, "
    "point-light energy, and image borders. Document the treatment of missing background samples."
)
FIXTURE = "A strongly defocused foreground branch crossing an in-focus face and a bright background light."
ORACLE = "The branch spreads appropriately without leaking background color through the opaque focused face."
MUTANT = "Apply one gather blur radius per pixel without any depth-order reasoning."
DELIVERABLE = "Occlusion-aware bokeh reference and layer-compositing tests"
OPEN_QUESTION = "physical S23 measurement was not run"

FOCUS_EPSILON = 1e-6
DEFOCUS_RADIUS_SCALE = 1.0
UNIFORM_GAUSSIAN_RADIUS = 4.0
FAR_DEPTH = 1_000_000.0
SAMPLE_KEYS = {"depth", "value", "layer"}
LAYERS = {"foreground", "focus", "background", "unknown"}
LABELS = {"depth-ordered", "optical_bokeh", "unknown-as-far", "uniform-background"}
BLUR_RULE = (
    "Depth-ordered normalized gather: radius = DEFOCUS_RADIUS_SCALE * abs(depth - focus); "
    "background mixes only with background; foreground mixes only with foreground and "
    "must not enter a background output bin; focus-plane neighbour weight is 0 within "
    "FOCUS_EPSILON; unknown depth stays unknown and is not treated as far; a uniform "
    "gaussian labelled optical_bokeh is rejected; border kernels are renormalized over "
    "in-strip admitted samples; missing background behind opaque focus is not invented."
)

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "focus",
    "samples",
    "claim",
    "label",
}
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


def _number(value: Any, name: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), name + " must be a number")
    number = float(value)
    require(math.isfinite(number), name + " must be finite")
    return number


def defocus_radius(depth: float, focus: float) -> float:
    """Gather radius in strip samples. Zero on the focus plane."""
    return DEFOCUS_RADIUS_SCALE * abs(depth - focus)


def on_focus_plane(depth: float, focus: float) -> bool:
    """True when depth equals focus within FOCUS_EPSILON, allowing one ulp."""
    return abs(depth - focus) <= FOCUS_EPSILON * (1.0 + 1e-9) + 1e-15


def classify_depth(depth: float | None, focus: float) -> str:
    if depth is None:
        return "unknown"
    if on_focus_plane(depth, focus):
        return "focus"
    if depth < focus:
        return "foreground"
    return "background"


def gaussian_weight(offset: int, radius: float) -> float:
    """Normalized-ready spatial weight. Neighbours outside the radius are 0.

    At radius 0 only the center sample has weight, and that weight is 1.
    """
    distance = abs(offset)
    if distance == 0:
        return 1.0
    if radius <= FOCUS_EPSILON or distance > radius:
        return 0.0
    sigma = max(radius / 2.0, FOCUS_EPSILON)
    return math.exp(-0.5 * (distance / sigma) ** 2)


def _evidence(value: Any) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            "evidenceId must be a non-empty string")
    return value


def validate_sample(sample: Any, focus: float, index: int) -> dict[str, Any]:
    require(isinstance(sample, dict), f"sample {index} must be an object")
    require(set(sample) == SAMPLE_KEYS, f"sample {index} keys must be depth, value, layer")
    layer = sample["layer"]
    require(isinstance(layer, str) and layer in LAYERS, f"sample {index} layer is invalid")
    value = _number(sample["value"], f"sample {index} value")
    raw_depth = sample["depth"]
    if raw_depth is None:
        require(layer == "unknown", f"sample {index} unknown depth requires layer unknown")
        depth = None
    else:
        require(layer != "unknown", f"sample {index} layer unknown requires a null depth")
        depth = _number(raw_depth, f"sample {index} depth")
    kind = classify_depth(depth, focus)
    require(kind == layer, f"sample {index} layer does not match depth order")
    return {"depth": depth, "value": value, "layer": layer}


def validate_strip(samples: Any, focus: float) -> list[dict[str, Any]]:
    require(isinstance(samples, list) and len(samples) >= 1, "samples must be a non-empty list")
    return [validate_sample(sample, focus, index) for index, sample in enumerate(samples)]


def _empty_output(index: int, sample: dict[str, Any], layer: str, radius: float, blurred: bool) -> dict[str, Any]:
    return {
        "index": index,
        "value": sample["value"],
        "layer": layer,
        "neighbourWeight": 0.0,
        "foregroundWeight": 0.0,
        "radius": radius,
        "kernelEnergy": 0.0 if layer == "unknown" else 1.0,
        "blurred": blurred,
    }


def render_depth_ordered(samples: list[dict], focus: float, *, unknown_as_far: bool = False) -> list[dict[str, Any]]:
    """Occlusion-aware layered gather.

    Each output bin keeps its source layer. Only that layer's samples are mixed,
    with a normalized kernel whose radius follows signed defocus. Focus bins do
    not take neighbour colour. Unknown bins are copied through unless the caller
    explicitly (and illegally, at the decision layer) treats them as far.
    """
    focus_value = _number(focus, "focus")
    prepared = validate_strip(samples, focus_value)
    working: list[dict[str, Any]] = []
    for sample in prepared:
        if sample["depth"] is None and unknown_as_far:
            rewritten = {
                "depth": FAR_DEPTH,
                "value": sample["value"],
                "layer": "background",
                "wasUnknown": True,
            }
            working.append(rewritten)
        else:
            working.append({**sample, "wasUnknown": sample["depth"] is None})
    classes = [
        "unknown" if item["wasUnknown"] and not unknown_as_far else classify_depth(item["depth"], focus_value)
        for item in working
    ]
    outputs: list[dict[str, Any]] = []
    for index, sample in enumerate(working):
        kind = classes[index]
        if sample["wasUnknown"] and not unknown_as_far:
            outputs.append(_empty_output(index, prepared[index], "unknown", 0.0, False))
            continue
        radius = defocus_radius(sample["depth"], focus_value)
        if kind == "focus" or radius <= FOCUS_EPSILON:
            # Neighbour mix weight is exactly 0 on the focus plane.
            output = _empty_output(index, prepared[index], kind if kind == "focus" else kind, 0.0, False)
            output["value"] = sample["value"]
            output["layer"] = "focus" if kind == "focus" else kind
            outputs.append(output)
            continue
        weights: list[tuple[int, float, str]] = []
        for other_index, other in enumerate(working):
            if classes[other_index] != kind:
                continue
            weight = gaussian_weight(other_index - index, radius)
            if weight <= 0.0:
                continue
            weights.append((other_index, weight, classes[other_index]))
        total = sum(weight for _, weight, _ in weights)
        require(total > 0.0, "kernel lost its center sample")
        mixed = 0.0
        neighbour = 0.0
        foreground = 0.0
        for other_index, weight, other_kind in weights:
            mixed += (weight / total) * working[other_index]["value"]
            if other_index != index:
                neighbour += weight / total
            if other_kind == "foreground":
                foreground += weight / total
        outputs.append({
            "index": index,
            "value": mixed,
            "layer": kind,
            "neighbourWeight": neighbour,
            "foregroundWeight": foreground if kind == "background" else 0.0,
            "radius": radius,
            "kernelEnergy": total / total,
            "blurred": neighbour > 0.0,
        })
    return outputs


def render_uniform_gaussian(samples: list[dict], focus: float, radius: float = UNIFORM_GAUSSIAN_RADIUS) -> list[dict[str, Any]]:
    """One radius, every sample, no depth order. This is not optical bokeh."""
    focus_value = _number(focus, "focus")
    prepared = validate_strip(samples, focus_value)
    require(radius > FOCUS_EPSILON, "uniform radius must be positive")
    outputs: list[dict[str, Any]] = []
    count = len(prepared)
    for index, sample in enumerate(prepared):
        weights: list[tuple[int, float]] = []
        for other_index in range(count):
            weight = gaussian_weight(other_index - index, radius)
            if weight > 0.0:
                weights.append((other_index, weight))
        total = sum(weight for _, weight in weights)
        mixed = 0.0
        neighbour = 0.0
        foreground = 0.0
        for other_index, weight in weights:
            share = weight / total
            mixed += share * prepared[other_index]["value"]
            if other_index != index:
                neighbour += share
            if prepared[other_index]["layer"] == "foreground":
                foreground += share
        outputs.append({
            "index": index,
            "value": mixed,
            "layer": sample["layer"],
            "neighbourWeight": neighbour,
            "foregroundWeight": foreground if sample["layer"] == "background" else 0.0,
            "radius": float(radius),
            "kernelEnergy": 1.0,
            "blurred": neighbour > 0.0,
        })
    return outputs


def render_unknown_as_far(samples: list[dict], focus: float) -> list[dict[str, Any]]:
    """Illegal mode: unknown depth is rewritten to FAR_DEPTH and blurred as background."""
    return render_depth_ordered(samples, focus, unknown_as_far=True)


def render_uniform_background_without_coverage(samples: list[dict], focus: float,
                                               radius: float = UNIFORM_GAUSSIAN_RADIUS) -> list[dict[str, Any]]:
    """Blur background with one radius and paint it through every pixel.

    There is no foreground or focus coverage mask, so the in-focus face takes
    background colour. That is the TC-P110-07 negative.
    """
    focus_value = _number(focus, "focus")
    prepared = validate_strip(samples, focus_value)
    background = [index for index, sample in enumerate(prepared) if sample["layer"] == "background"]
    require(background, "uniform background blur needs a background sample")
    outputs: list[dict[str, Any]] = []
    for index, sample in enumerate(prepared):
        weights: list[tuple[int, float]] = []
        for other_index in background:
            weight = gaussian_weight(other_index - index, radius)
            if weight > 0.0:
                weights.append((other_index, weight))
        if not weights:
            nearest = min(background, key=lambda item: abs(item - index))
            weights = [(nearest, 1.0)]
        total = sum(weight for _, weight in weights)
        mixed = sum((weight / total) * prepared[other]["value"] for other, weight in weights)
        outputs.append({
            "index": index,
            "value": mixed,
            "layer": sample["layer"],
            "neighbourWeight": 0.0 if sample["layer"] == "focus" and abs(mixed - sample["value"]) <= FOCUS_EPSILON else 1.0,
            "foregroundWeight": 0.0,
            "radius": float(radius),
            "kernelEnergy": 1.0,
            "blurred": True,
            "backgroundLeak": sample["layer"] in {"focus", "foreground", "unknown"} and abs(mixed - sample["value"]) > 1e-9,
        })
    return outputs


def audit_outputs(samples: list[dict], outputs: list[dict], focus: float) -> list[str]:
    """Return fault tokens for a render that claims to be depth-ordered."""
    focus_value = _number(focus, "focus")
    prepared = validate_strip(samples, focus_value)
    require(len(outputs) == len(prepared), "output length drifted")
    faults: list[str] = []
    for sample, output in zip(prepared, outputs):
        if sample["layer"] == "focus":
            if output["neighbourWeight"] != 0.0 or output["value"] != sample["value"]:
                faults.append("focus-plane-blurred")
        elif sample["layer"] == "unknown":
            if (
                output["layer"] != "unknown"
                or output["value"] != sample["value"]
                or output["neighbourWeight"] != 0.0
                or output["blurred"]
            ):
                faults.append("unknown-depth-blurred")
        elif sample["layer"] == "background":
            if output["foregroundWeight"] > 0.0:
                faults.append("foreground-bleed")
            if abs(output["kernelEnergy"] - 1.0) > 1e-9:
                faults.append("unnormalized-kernel")
        elif sample["layer"] == "foreground" and output["layer"] == "background":
            faults.append("foreground-bleed")
    return list(dict.fromkeys(faults))


def _foreground_values_in_background(samples: list[dict], outputs: list[dict]) -> bool:
    """True when a foreground sample contributed weight to a background bin."""
    for sample, output in zip(samples, outputs):
        if sample["layer"] == "background" and output.get("foregroundWeight", 0.0) > 0.0:
            return True
    return False


def _result(decision: str, reasons: list[str], rejected: list[str], evidence: str, claim: str) -> dict[str, Any]:
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, claim],
        "openQuestions": [
            OPEN_QUESTION,
            "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
            "missing background behind the opaque focus face is not invented",
            "border kernels are renormalized over in-strip admitted samples",
        ],
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Record a depth-ordered strip or reject a depth-blind blur."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _evidence(document["evidenceId"])
    claim = document["claim"]
    require(isinstance(claim, str) and claim.strip(), "claim must be a non-empty string")
    label = document["label"]
    require(isinstance(label, str) and label in LABELS, "label is invalid")
    if claim == "optical_bokeh":
        label = "optical_bokeh"
    focus = _number(document["focus"], "focus")
    samples = validate_strip(document["samples"], focus)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "blur rule: " + BLUR_RULE,
    ]
    rejected: list[str] = []
    if label == "depth-ordered":
        outputs = render_depth_ordered(samples, focus)
        rejected.extend(audit_outputs(samples, outputs, focus))
        if _foreground_values_in_background(samples, outputs):
            rejected.append("foreground-bleed")
        reasons.append(_summary(samples, outputs))
        decision = "rejected" if rejected else "recorded"
        if decision == "recorded":
            reasons.append("depth-ordered host strip retained for " + evidence)
            reasons.append("method: " + METHOD)
    elif label == "optical_bokeh":
        outputs = render_uniform_gaussian(samples, focus)
        rejected.append("optical_bokeh")
        rejected.append(MUTANT)
        if _foreground_values_in_background(samples, outputs) or any(
            output["foregroundWeight"] > 0.0 for output in outputs
        ):
            rejected.append("foreground-bleed")
        if any(sample["layer"] == "focus" and output["neighbourWeight"] != 0.0
               for sample, output in zip(samples, outputs)):
            rejected.append("focus-plane-blurred")
        reasons.append("mutant rejected: " + MUTANT)
        reasons.append(_summary(samples, outputs))
        decision = "rejected"
    elif label == "unknown-as-far":
        outputs = render_unknown_as_far(samples, focus)
        rejected.append("unknown-treated-as-far")
        reasons.append("unknown depth was rewritten to FAR_DEPTH and blurred as background")
        reasons.append(_summary(samples, outputs))
        decision = "rejected"
    elif label == "uniform-background":
        outputs = render_uniform_background_without_coverage(samples, focus)
        rejected.append("uniform-background-blur-without-foreground-coverage")
        rejected.append(MUTANT)
        if any(output.get("backgroundLeak") for output in outputs):
            rejected.append("background-leak-through-focus")
        reasons.append("uniform background blur had no foreground coverage model")
        reasons.append(_summary(samples, outputs))
        decision = "rejected"
    else:
        raise ValueError("label is invalid")
    rejected = list(dict.fromkeys(rejected))
    return _result(decision, reasons, rejected, evidence, claim)


def _summary(samples: list[dict], outputs: list[dict]) -> str:
    parts = []
    for sample, output in zip(samples, outputs):
        parts.append(
            f"{sample['layer']}:{output['value']:.6g}:nw={output['neighbourWeight']:.6g}:fw={output['foregroundWeight']:.6g}"
        )
    return "outputs " + ",".join(parts)
