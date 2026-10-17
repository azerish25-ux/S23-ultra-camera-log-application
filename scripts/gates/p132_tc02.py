"""TC-P132-02 Source-look label confusion.

Host reference. The source domain and the display-scope label stay independent.
Renaming the source after a virtual format, or showing a display histogram as
sensor exposure, is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P132-02",
    "phase": "P132",
    "workstream": 17,
    "name": "Source-look label confusion",
    "intervention": (
        "Select a large-format film recipe while the underlying source remains a "
        "lower-resolution SDR or experimental RAW route."
    ),
    "expected": "Display the actual source and simulated look independently with their evidence status.",
    "negative": "Renaming a source mode after the virtual format must fail.",
    "repeat": "Repeat preset changes, saved recipe reopening, and export sharing.",
}

NEGATIVE_TOKEN = "renamed-source-mode-after-virtual-format"
LOOK_HIDDEN = "look-not-displayed-independently"
EVIDENCE_QUALIFIED = "evidence-status-qualified-or-allowed"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "scopes",
    "source",
    "applyMutant",
    "displayedSourceDomain",
    "displayedHistogramDomain",
    "displayedHistogramLabel",
    "virtualFormatName",
    "sourceEvidenceStatus",
    "lookEvidenceStatus",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p132_build_scopes_with_declared_signal_domains.py"
    spec = importlib.util.spec_from_file_location("p132_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    displayed_source = _GATE.require_text(payload["displayedSourceDomain"], "displayedSourceDomain")
    displayed_domain = _GATE.require_text(payload["displayedHistogramDomain"], "displayedHistogramDomain")
    displayed_label = _GATE.require_text(payload["displayedHistogramLabel"], "displayedHistogramLabel")
    virtual = _GATE.require_text(payload["virtualFormatName"], "virtualFormatName")
    source_evidence = _GATE.require_text(payload["sourceEvidenceStatus"], "sourceEvidenceStatus")
    look_evidence = _GATE.require_text(payload["lookEvidenceStatus"], "lookEvidenceStatus")
    info = bundle["info"]
    histogram = _GATE.scope_by_kind(info, "histogram")
    renamed = (
        displayed_source != info["sourceDomain"]
        or displayed_domain != histogram["domain"]
        or displayed_label != histogram["label"]
        or displayed_source.casefold() == virtual.casefold()
    )
    if renamed:
        faults.append(NEGATIVE_TOKEN)
    if displayed_label == histogram["label"] and displayed_domain == histogram["domain"]:
        independent = displayed_source != displayed_label
    else:
        independent = False
    if not independent:
        faults.append(LOOK_HIDDEN)
    if source_evidence.casefold() in {"qualified", "allowed"} or look_evidence.casefold() in {"qualified", "allowed"}:
        faults.append(EVIDENCE_QUALIFIED)
    extra = [{
        "displayedSourceDomain": displayed_source,
        "displayedHistogramDomain": displayed_domain,
        "displayedHistogramLabel": displayed_label,
        "virtualFormatName": virtual,
        "sourceEvidenceStatus": source_evidence,
        "lookEvidenceStatus": look_evidence,
        "sourceClippingCount": info["sourceClippingCount"],
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        LOOK_HIDDEN: "the simulated look must be displayed independently of the source domain",
        EVIDENCE_QUALIFIED: "source or look evidence must not be marked qualified or allowed",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
