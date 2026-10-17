"""TC-P133-04 Stale or wrong-domain scope.

Host reference. Freshness and measurement domain are spoken by the monitoring
control. An RGB8 preview histogram must not certify source bit depth or sensor
clipping.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P133-04",
    "phase": "P133",
    "workstream": 17,
    "name": "Stale or wrong-domain scope",
    "intervention": "Feed a monitoring aid delayed preview samples or a display-clipped image from an unclipped source.",
    "expected": "Identify freshness and measurement domain instead of falsely reporting sensor conditions.",
    "negative": "An RGB8 preview histogram must not certify source bit depth or sensor clipping.",
    "repeat": "Repeat waveform, false color, focus peaking, and color histogram.",
}

NEGATIVE_TOKEN = "rgb8-preview-certifies-source-bit-depth-or-clipping"
STALE_CERTIFIES = "stale-scope-reports-sensor-conditions"
DOMAIN_UNSPOKEN = "measurement-domain-not-spoken"
DOMAINS = frozenset({
    "rgb8-preview",
    "source",
    "waveform",
    "false-color",
    "focus-peaking",
    "color-histogram",
})
POSITIVE_CLAIMS = (
    "certifies source bit depth",
    "certifies sensor clipping",
    "source bit depth certified",
    "sensor clipping certified",
)
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "focusOrder",
    "aidId",
    "measurementDomain",
    "fresh",
    "certifiesSourceBitDepth",
    "certifiesSensorClipping",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p133_implement_accessible_focus_and_recipe_controls.py"
    spec = importlib.util.spec_from_file_location("p133_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _claims(text: str) -> bool:
    folded = text.casefold()
    return any(phrase in folded for phrase in POSITIVE_CLAIMS)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    aid_id = _GATE.require_text(payload["aidId"], "aidId")
    domain = _GATE.require_text(payload["measurementDomain"], "measurementDomain")
    _GATE.require(domain in DOMAINS, "measurementDomain is not recognized")
    fresh = _GATE.require_bool(payload["fresh"], "fresh")
    certifies_depth = _GATE.require_bool(payload["certifiesSourceBitDepth"], "certifiesSourceBitDepth")
    certifies_clip = _GATE.require_bool(payload["certifiesSensorClipping"], "certifiesSensorClipping")
    aid = _GATE.find_control(bundle["controls"], aid_id)
    _GATE.require(aid is not None, "aidId is not on the surface")
    _GATE.require(aid["family"] == "monitoring", "aidId must be a monitoring control")
    spoken = aid["state_description"].casefold()
    freshness = "fresh" if fresh else "stale"
    if domain == "rgb8-preview" and (certifies_depth or certifies_clip or _claims(aid["state_description"])):
        faults.append(NEGATIVE_TOKEN)
    if not fresh and (certifies_depth or certifies_clip or _claims(aid["state_description"])):
        faults.append(STALE_CERTIFIES)
    if domain not in spoken or freshness not in spoken:
        faults.append(DOMAIN_UNSPOKEN)
    extra = [
        "measurementDomain=" + domain,
        "freshness=" + freshness,
        {
            "aidId": aid_id,
            "measurementDomain": domain,
            "fresh": fresh,
            "certifiesSourceBitDepth": certifies_depth,
            "certifiesSensorClipping": certifies_clip,
            "spokenState": aid["state_description"],
        },
    ]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        STALE_CERTIFIES: "a stale scope must not report sensor clipping or source bit depth",
        DOMAIN_UNSPOKEN: "freshness and measurement domain must be spoken",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
