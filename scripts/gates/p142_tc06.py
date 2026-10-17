"""TC-P142-06 Reference edition conflict.

Host reference. Theatrical, digital, HDR, and unidentified references stay
separate when their appearance disagrees. Averaging them into one historical
fact is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-06",
    "phase": "P142",
    "workstream": 18,
    "name": "Reference edition conflict",
    "intervention": "Supply references from different film releases or display assumptions with different appearance.",
    "expected": "Keep separate targets or explicit uncertainty rather than inventing one definitive look.",
    "negative": "Averaging inconsistent editions into a historical fact must fail.",
    "repeat": "Repeat theatrical, digital, HDR, and unidentified reference versions.",
}

NEGATIVE_TOKEN = "averaged-inconsistent-editions-into-historical-fact"
INVENTED = "invented-one-definitive-look"
EDITION_KEYS = {"id", "release", "display", "contrast", "saturation"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "source",
    "reference",
    "suggestion",
    "editions",
    "separateTargets",
    "uncertaintyExplicit",
    "averagedIntoHistoricalFact",
    "definitiveLook",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def clean_editions():
    return [
        {"id": "theatrical", "release": "theatrical", "display": "theatrical", "contrast": 1.1, "saturation": 0.8},
        {"id": "digital", "release": "digital", "display": "rec709", "contrast": 1.25, "saturation": 0.9},
        {"id": "hdr", "release": "hdr", "display": "hdr", "contrast": 1.6, "saturation": 1.05},
        {"id": "unidentified", "release": "unidentified", "display": "unknown", "contrast": 1.0, "saturation": 1.0},
    ]


def _spread(values: list[float]) -> float:
    return max(values) - min(values)


def editions_conflict(editions: list[dict]) -> bool:
    if _spread([item["contrast"] for item in editions]) > 1e-6:
        return True
    if _spread([item["saturation"] for item in editions]) > 1e-6:
        return True
    return len({item["display"] for item in editions}) > 1


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    raw = payload["editions"]
    _GATE.require(isinstance(raw, list) and len(raw) >= 2, "editions needs at least two references")
    editions = []
    seen = set()
    for index, item in enumerate(raw):
        label = "editions[" + str(index) + "]"
        _GATE.require(isinstance(item, dict) and set(item) == EDITION_KEYS, label + " keys are invalid")
        edition_id = _GATE.require_text(item["id"], label + ".id")
        _GATE.require(edition_id not in seen, "duplicate edition id")
        seen.add(edition_id)
        editions.append({
            "id": edition_id,
            "release": _GATE.require_text(item["release"], label + ".release"),
            "display": _GATE.require_text(item["display"], label + ".display"),
            "contrast": _GATE.require_number(item["contrast"], label + ".contrast"),
            "saturation": _GATE.require_number(item["saturation"], label + ".saturation"),
        })
    separate = _GATE.require_bool(payload["separateTargets"], "separateTargets")
    uncertainty = _GATE.require_bool(payload["uncertaintyExplicit"], "uncertaintyExplicit")
    averaged = _GATE.require_bool(payload["averagedIntoHistoricalFact"], "averagedIntoHistoricalFact")
    definitive = payload["definitiveLook"]
    if definitive is not None:
        definitive = _GATE.require_text(definitive, "definitiveLook")
    conflict = editions_conflict(editions)
    if conflict and averaged:
        faults.append(NEGATIVE_TOKEN)
    if conflict and definitive is not None:
        faults.append(INVENTED)
    if conflict and not separate and not uncertainty:
        faults.append(INVENTED)
    extra = [{
        "conflict": conflict,
        "editionIds": [item["id"] for item in editions],
        "separateTargets": separate,
        "uncertaintyExplicit": uncertainty,
        "definitiveLook": definitive,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            INVENTED: CASE["expected"],
        },
    )
