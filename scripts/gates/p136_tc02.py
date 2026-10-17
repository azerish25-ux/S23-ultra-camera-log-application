"""TC-P136-02 Source-look label confusion.

Host fixture. The actual source and a simulated look stay independent.
Renaming the source mode after the virtual format is rejected.
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
    "id": "TC-P136-02",
    "phase": "P136",
    "workstream": 17,
    "name": "Source-look label confusion",
    "intervention": "Select a large-format film recipe while the underlying source remains a lower-resolution SDR or experimental RAW route.",
    "expected": "Display the actual source and simulated look independently with their evidence status.",
    "negative": "Renaming a source mode after the virtual format must fail.",
    "repeat": "Repeat preset changes, saved recipe reopening, and export sharing.",
}
NEGATIVE_TOKEN = "renamed-source-mode-after-virtual-format"
NOT_INDEPENDENT = "source-and-look-not-independent"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "sourceMode",
    "virtualFormat",
    "displayedSource",
    "displayedLook",
    "lookSimulated",
    "sourceEvidence",
    "lookEvidence",
    "renamedSourceAfterFormat",
}


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    source_mode = _GATE.require_text(payload["sourceMode"], "sourceMode")
    virtual_format = _GATE.require_text(payload["virtualFormat"], "virtualFormat")
    displayed_source = _GATE.require_text(payload["displayedSource"], "displayedSource")
    displayed_look = _GATE.require_text(payload["displayedLook"], "displayedLook")
    look_simulated = _GATE.require_bool(payload["lookSimulated"], "lookSimulated")
    source_evidence = _GATE.require_text(payload["sourceEvidence"], "sourceEvidence")
    look_evidence = _GATE.require_text(payload["lookEvidence"], "lookEvidence")
    renamed_flag = _GATE.require_bool(payload["renamedSourceAfterFormat"], "renamedSourceAfterFormat")
    source_norm = _norm(source_mode)
    virtual_norm = _norm(virtual_format)
    displayed_norm = _norm(displayed_source)
    renamed = renamed_flag or (displayed_norm == virtual_norm and displayed_norm != source_norm)
    independent = (
        _norm(displayed_source) != _norm(displayed_look)
        and displayed_norm == source_norm
        and look_simulated
        and source_evidence != look_evidence
    )
    faults = []
    if renamed or displayed_norm != source_norm:
        faults.append(NEGATIVE_TOKEN)
    if not independent:
        faults.append(NOT_INDEPENDENT)
    reasons = [
        f"sourceMode={source_mode} displayedSource={displayed_source} virtualFormat={virtual_format}",
        f"displayedLook={displayed_look} lookSimulated={str(look_simulated).lower()}",
        f"sourceEvidence={source_evidence} lookEvidence={look_evidence}",
    ]
    preserved = [{
        "sourceMode": source_mode,
        "virtualFormat": virtual_format,
        "displayedSource": displayed_source,
        "displayedLook": displayed_look,
        "lookSimulated": look_simulated,
        "sourceEvidence": source_evidence,
        "lookEvidence": look_evidence,
        "renamed": renamed,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            NOT_INDEPENDENT: CASE["expected"],
        },
        {
            NEGATIVE_TOKEN: "Do not rename the source mode after the virtual format.",
            NOT_INDEPENDENT: "Show the actual source and the simulated look with separate evidence.",
        },
    )
