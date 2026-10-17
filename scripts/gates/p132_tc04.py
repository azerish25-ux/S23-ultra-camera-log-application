"""TC-P132-04 Stale or wrong-domain scope.

Host reference. Freshness and measurement domain are identified. An RGB8
preview must not certify source bit depth or sensor clipping. Clipping counts
from the display preview stay distinct from the unclipped source.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P132-04",
    "phase": "P132",
    "workstream": 17,
    "name": "Stale or wrong-domain scope",
    "intervention": "Feed a monitoring aid delayed preview samples or a display-clipped image from an unclipped source.",
    "expected": "Identify freshness and measurement domain instead of falsely reporting sensor conditions.",
    "negative": "An RGB8 preview histogram must not certify source bit depth or sensor clipping.",
    "repeat": "Repeat waveform, false color, focus peaking, and color histogram.",
}

NEGATIVE_TOKEN = "rgb8-preview-certifies-source-bit-depth-or-clipping"
WRONG_DOMAIN = "reported-domain-disagrees-with-scope"
FRESHNESS_MISREPORTED = "reported-freshness-disagrees-with-scope"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "scopes",
    "source",
    "applyMutant",
    "reportedDomain",
    "reportedFresh",
    "certifiesSourceBitDepth",
    "certifiesSensorClipping",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p132_build_scopes_with_declared_signal_domains.py"
    spec = importlib.util.spec_from_file_location("p132_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    reported_domain = _GATE.require_text(payload["reportedDomain"], "reportedDomain")
    _GATE.require(
        reported_domain in _GATE.DOMAINS or reported_domain == "missing",
        "reportedDomain is not a signal domain",
    )
    reported_fresh = _GATE.require_bool(payload["reportedFresh"], "reportedFresh")
    certifies_depth = _GATE.require_bool(payload["certifiesSourceBitDepth"], "certifiesSourceBitDepth")
    certifies_clip = _GATE.require_bool(payload["certifiesSensorClipping"], "certifiesSensorClipping")
    waveform = _GATE.scope_by_id(bundle["info"], "stale-waveform")
    if reported_domain != waveform["domain"]:
        faults.append(WRONG_DOMAIN)
    if reported_fresh != waveform["fresh"]:
        faults.append(FRESHNESS_MISREPORTED)
    if certifies_depth or certifies_clip:
        faults.append(NEGATIVE_TOKEN)
    freshness = "fresh" if waveform["fresh"] else "stale"
    extra = [
        "measurementDomain=" + waveform["domain"],
        "freshness=" + freshness,
        {
            "reportedDomain": reported_domain,
            "reportedFresh": reported_fresh,
            "certifiesSourceBitDepth": certifies_depth,
            "certifiesSensorClipping": certifies_clip,
            "sourceClippingCount": bundle["info"]["sourceClippingCount"],
            "previewClippingCount": bundle["info"]["previewClippingCount"],
        },
    ]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        WRONG_DOMAIN: "the reported measurement domain must match the scope domain",
        FRESHNESS_MISREPORTED: "stale status must be identified rather than hidden",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
