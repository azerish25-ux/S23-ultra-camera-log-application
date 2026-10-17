"""TC-P134-02 Source-look label confusion.

Host reference. The actual source and the simulated look stay independent.
Renaming a source mode after the virtual format is rejected. Progress is not
relabelled as a completed large-format capture.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P134-02",
    "phase": "P134",
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
LOOK_EVIDENCE_QUALIFIED = "look-evidence-marked-qualified"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "progress",
    "sourceId",
    "lookId",
    "virtualFormat",
    "displayedSourceId",
    "displayedLookId",
    "sourceEvidenceStatus",
    "lookEvidenceStatus",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p134_design_transparent_progress_and_failure_states.py"
    spec = importlib.util.spec_from_file_location("p134_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    source_id = _GATE.require_text(payload["sourceId"], "sourceId")
    look_id = _GATE.require_text(payload["lookId"], "lookId")
    virtual_format = _GATE.require_text(payload["virtualFormat"], "virtualFormat")
    displayed_source = _GATE.require_text(payload["displayedSourceId"], "displayedSourceId")
    displayed_look = _GATE.require_text(payload["displayedLookId"], "displayedLookId")
    source_evidence = _GATE.require_text(payload["sourceEvidenceStatus"], "sourceEvidenceStatus")
    look_evidence = _GATE.require_text(payload["lookEvidenceStatus"], "lookEvidenceStatus")
    renamed = (
        displayed_source != source_id
        or displayed_source == virtual_format
        or virtual_format.casefold() in displayed_source.casefold()
        or source_evidence.casefold() in {"qualified", "allowed"}
    )
    if renamed:
        faults.append(NEGATIVE_TOKEN)
    if displayed_look != look_id:
        faults.append(LOOK_HIDDEN)
    large = any(token in look_id.casefold() for token in ("imax", "70mm", "large-format", "large format"))
    if large and look_evidence != "simulated":
        faults.append(_GATE.PREMATURE_COMPLETE if look_evidence.casefold() in {"qualified", "allowed"} else LOOK_HIDDEN)
        if look_evidence != "simulated":
            faults.append("large-format-look-not-simulated")
    if look_evidence.casefold() in {"qualified", "allowed"}:
        faults.append(LOOK_EVIDENCE_QUALIFIED)
    extra = [{
        "sourceId": source_id,
        "lookId": look_id,
        "virtualFormat": virtual_format,
        "displayedSourceId": displayed_source,
        "displayedLookId": displayed_look,
        "sourceEvidenceStatus": source_evidence,
        "lookEvidenceStatus": look_evidence,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        LOOK_HIDDEN: "the simulated look must be displayed independently of the source",
        LOOK_EVIDENCE_QUALIFIED: "look evidence must not be marked qualified or allowed",
        "large-format-look-not-simulated": "a large-format appearance must be labelled simulated",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
