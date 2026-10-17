"""TC-P136-04 Stale or wrong-domain scope.

Host fixture. Freshness and measurement domain stay explicit. An RGB8 preview
histogram must not certify source bit depth or sensor clipping.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_run_usability_acceptance_on_the_physical_phone",
    Path(__file__).resolve().parent / "p136_run_usability_acceptance_on_the_physical_phone.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE = {
    "id": "TC-P136-04",
    "phase": "P136",
    "workstream": 17,
    "name": "Stale or wrong-domain scope",
    "intervention": "Feed a monitoring aid delayed preview samples or a display-clipped image from an unclipped source.",
    "expected": "Identify freshness and measurement domain instead of falsely reporting sensor conditions.",
    "negative": "An RGB8 preview histogram must not certify source bit depth or sensor clipping.",
    "repeat": "Repeat waveform, false color, focus peaking, and color histogram.",
}
NEGATIVE_TOKEN = "rgb8-preview-histogram-certified-source"
WRONG_DOMAIN = "wrong-domain-reported-as-sensor"
AIDS = frozenset({"waveform", "false-color", "focus-peaking", "histogram"})
DOMAINS = frozenset({"preview-rgb8", "source", "display"})
FRESHNESS = frozenset({"fresh", "delayed"})
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "aid",
    "sampleDomain",
    "freshness",
    "sourceClipped",
    "reportedSensorClipping",
    "sourceBitDepth",
    "reportedBitDepth",
    "certifiesSource",
}


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    aid = _GATE.require_text(payload["aid"], "aid")
    domain = _GATE.require_text(payload["sampleDomain"], "sampleDomain")
    freshness = _GATE.require_text(payload["freshness"], "freshness")
    _GATE.require(aid in AIDS, "aid is not recognized")
    _GATE.require(domain in DOMAINS, "sampleDomain is not recognized")
    _GATE.require(freshness in FRESHNESS, "freshness is not recognized")
    source_clipped = _GATE.require_bool(payload["sourceClipped"], "sourceClipped")
    reported_clip = _GATE.require_bool(payload["reportedSensorClipping"], "reportedSensorClipping")
    source_depth = payload["sourceBitDepth"]
    _GATE.require(type(source_depth) is int and source_depth > 0, "sourceBitDepth must be a positive int")
    reported_depth = payload["reportedBitDepth"]
    if reported_depth is not None:
        _GATE.require(type(reported_depth) is int and reported_depth > 0, "reportedBitDepth must be a positive int or null")
    certifies = _GATE.require_bool(payload["certifiesSource"], "certifiesSource")
    rgb8_histogram = aid == "histogram" and domain == "preview-rgb8"
    certifies_depth = reported_depth is not None and reported_depth == source_depth and rgb8_histogram
    faults = []
    if rgb8_histogram and (certifies or reported_clip or certifies_depth):
        faults.append(NEGATIVE_TOKEN)
    if domain != "source" and reported_clip:
        faults.append(WRONG_DOMAIN)
    if freshness == "delayed" and reported_clip:
        if WRONG_DOMAIN not in faults:
            faults.append(WRONG_DOMAIN)
    reasons = [
        f"aid={aid} sampleDomain={domain} freshness={freshness}",
        f"sourceClipped={str(source_clipped).lower()} reportedSensorClipping={str(reported_clip).lower()}",
        f"sourceBitDepth={source_depth} reportedBitDepth={reported_depth} certifiesSource={str(certifies).lower()}",
    ]
    preserved = [{
        "aid": aid,
        "sampleDomain": domain,
        "freshness": freshness,
        "sourceClipped": source_clipped,
        "reportedSensorClipping": reported_clip,
        "sourceBitDepth": source_depth,
        "reportedBitDepth": reported_depth,
        "certifiesSource": certifies,
        "rgb8Histogram": rgb8_histogram,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {NEGATIVE_TOKEN: CASE["negative"], WRONG_DOMAIN: CASE["expected"]},
        {
            NEGATIVE_TOKEN: "Do not let an RGB8 preview histogram certify source bit depth or sensor clipping.",
            WRONG_DOMAIN: "Label freshness and measurement domain instead of reporting sensor conditions.",
        },
    )
