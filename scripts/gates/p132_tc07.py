"""TC-P132-07 Unfair comparison view.

Host reference. A display-domain scope and the sensor-domain source are not
the same signal. Preference without a disclosed mismatch is rejected, and
automatically enhancing one side is rejected.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE = {
    "id": "TC-P132-07",
    "phase": "P132",
    "workstream": 17,
    "name": "Unfair comparison view",
    "intervention": "Compare outputs at different times, scales, or display transforms without making those differences visible.",
    "expected": "Align comparable content or clearly disclose the mismatch before presenting a preference judgment.",
    "negative": "Automatically enhancing one side of a comparison must fail.",
    "repeat": "Repeat source-versus-result, recipe revisions, and different output aspect ratios.",
}

NEGATIVE_TOKEN = "auto-enhanced-comparison-side"
UNDISCLOSED = "undisclosed-comparison-mismatch"
DOMAIN_MISMATCH = "comparison-domain-does-not-match-scope"
SIDE_KEYS = {"scale", "transfer", "enhanced", "time"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "scopes",
    "source",
    "applyMutant",
    "left",
    "right",
    "mismatchDisclosed",
    "preferenceJudgment",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p132_build_scopes_with_declared_signal_domains.py"
    spec = importlib.util.spec_from_file_location("p132_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _side(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == SIDE_KEYS, label + " keys are invalid")
    scale = _GATE.require_number(value["scale"], label + ".scale")
    _GATE.require(scale > 0, label + ".scale must be positive")
    return {
        "scale": scale,
        "transfer": _GATE.require_text(value["transfer"], label + ".transfer"),
        "enhanced": _GATE.require_bool(value["enhanced"], label + ".enhanced"),
        "time": _GATE.require_number(value["time"], label + ".time"),
    }


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    left = _side(payload["left"], "left")
    right = _side(payload["right"], "right")
    disclosed = _GATE.require_bool(payload["mismatchDisclosed"], "mismatchDisclosed")
    preference = _GATE.require_bool(payload["preferenceJudgment"], "preferenceJudgment")
    info = bundle["info"]
    histogram = _GATE.scope_by_kind(info, "histogram")
    if left["enhanced"] or right["enhanced"]:
        faults.append(NEGATIVE_TOKEN)
    shown_differs = (
        left["transfer"] != right["transfer"]
        or not _close(left["scale"], right["scale"])
        or not _close(left["time"], right["time"])
    )
    actual_differs = histogram["domain"] != info["sourceDomain"] or shown_differs
    lied = left["transfer"] != histogram["domain"] or right["transfer"] != info["sourceDomain"]
    if lied:
        faults.append(DOMAIN_MISMATCH)
    if actual_differs and preference and not disclosed:
        faults.append(UNDISCLOSED)
    extra = [{
        "mismatch": actual_differs,
        "shownMismatch": shown_differs,
        "mismatchDisclosed": disclosed,
        "preferenceJudgment": preference,
        "leftEnhanced": left["enhanced"],
        "rightEnhanced": right["enhanced"],
        "histogramDomain": histogram["domain"],
        "sourceDomain": info["sourceDomain"],
        "previewClippingCount": info["previewClippingCount"],
        "sourceClippingCount": info["sourceClippingCount"],
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        UNDISCLOSED: "a preference requires aligned content or a disclosed mismatch",
        DOMAIN_MISMATCH: "comparison sides must name the histogram domain and the source domain",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
