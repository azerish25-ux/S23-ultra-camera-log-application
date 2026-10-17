"""TC-P131-02 Source-look label confusion.

Host reference. The displayed source stays the recording configuration while a
simulated look is labelled separately. Renaming the source after a virtual
format is rejected. The shutter draft still does not move the applied value.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P131-02",
    "phase": "P131",
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
UNIT_HIDDEN = "unit-not-visible"
LOOK_QUALIFIED = "look-evidence-marked-qualified"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "committed",
    "proposed",
    "displayedSource",
    "displayedLook",
    "displayedUnit",
    "sourceEvidenceStatus",
    "lookEvidenceStatus",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p131_design_manual_controls_for_deliberate_operation.py"
    spec = importlib.util.spec_from_file_location("p131_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    displayed_source = _GATE.require_text(payload["displayedSource"], "displayedSource")
    displayed_look = _GATE.require_text(payload["displayedLook"], "displayedLook")
    displayed_unit = _GATE.require_text(payload["displayedUnit"], "displayedUnit")
    source_evidence = _GATE.require_text(payload["sourceEvidenceStatus"], "sourceEvidenceStatus")
    look_evidence = _GATE.require_text(payload["lookEvidenceStatus"], "lookEvidenceStatus")
    source = bundle["committed"]["source_configuration"]
    renamed = displayed_source != source or source_evidence.casefold() in {"qualified", "allowed"}
    if displayed_look.casefold() in displayed_source.casefold() and displayed_look.casefold() not in source.casefold():
        renamed = True
    if renamed:
        faults.append(NEGATIVE_TOKEN)
    if displayed_look == displayed_source:
        faults.append(LOOK_HIDDEN)
    if displayed_unit != bundle["committed"]["unit"]:
        faults.append(UNIT_HIDDEN)
    if look_evidence.casefold() in {"qualified", "allowed"}:
        faults.append(LOOK_QUALIFIED)
    extra = [{
        "displayedSource": displayed_source,
        "displayedLook": displayed_look,
        "displayedUnit": displayed_unit,
        "sourceEvidenceStatus": source_evidence,
        "lookEvidenceStatus": look_evidence,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        LOOK_HIDDEN: "the simulated look must be displayed independently of the source",
        UNIT_HIDDEN: "the control unit must stay visible",
        LOOK_QUALIFIED: "look evidence must not be marked qualified or allowed",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
