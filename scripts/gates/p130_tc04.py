"""TC-P130-04 Stale or wrong-domain scope.

Host reference. Freshness and measurement domain are identified. An RGB8
preview histogram must not certify source bit depth or sensor clipping, and a
look selection must not rewrite the source.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P130-04",
    "phase": "P130",
    "workstream": 17,
    "name": "Stale or wrong-domain scope",
    "intervention": "Feed a monitoring aid delayed preview samples or a display-clipped image from an unclipped source.",
    "expected": "Identify freshness and measurement domain instead of falsely reporting sensor conditions.",
    "negative": "An RGB8 preview histogram must not certify source bit depth or sensor clipping.",
    "repeat": "Repeat waveform, false color, focus peaking, and color histogram.",
}

NEGATIVE_TOKEN = "rgb8-preview-certifies-source-bit-depth-or-clipping"
STALE_CERTIFIES = "stale-scope-reports-sensor-conditions"
DOMAINS = frozenset({
    "rgb8-preview",
    "source",
    "waveform",
    "false-color",
    "focus-peaking",
    "color-histogram",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "committed",
    "proposed",
    "measurementDomain",
    "fresh",
    "certifiesSourceBitDepth",
    "certifiesSensorClipping",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p130_implement_source_and_look_selection_separately.py"
    spec = importlib.util.spec_from_file_location("p130_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    domain = _GATE.require_text(payload["measurementDomain"], "measurementDomain")
    _GATE.require(domain in DOMAINS, "measurementDomain is not recognized")
    fresh = _GATE.require_bool(payload["fresh"], "fresh")
    certifies_depth = _GATE.require_bool(payload["certifiesSourceBitDepth"], "certifiesSourceBitDepth")
    certifies_clip = _GATE.require_bool(payload["certifiesSensorClipping"], "certifiesSensorClipping")
    if domain == "rgb8-preview" and (certifies_depth or certifies_clip):
        faults.append(NEGATIVE_TOKEN)
    if not fresh and (certifies_depth or certifies_clip):
        faults.append(STALE_CERTIFIES)
    freshness = "fresh" if fresh else "stale"
    extra = [
        "measurementDomain=" + domain,
        "freshness=" + freshness,
        {
            "measurementDomain": domain,
            "fresh": fresh,
            "certifiesSourceBitDepth": certifies_depth,
            "certifiesSensorClipping": certifies_clip,
        },
    ]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        STALE_CERTIFIES: "a stale scope must not report sensor clipping or source bit depth",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
