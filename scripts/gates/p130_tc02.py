"""TC-P130-02 Source-look label confusion.

Host reference. The displayed source and the simulated look stay independent.
Renaming the source mode after a virtual format, including an IMAX 70mm
relabel, is rejected. Look edits do not rewrite source_id, source_sha256, or
source_transfer.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P130-02",
    "phase": "P130",
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
    "committed",
    "proposed",
    "displayedSourceId",
    "displayedLookId",
    "displayedTransfer",
    "sourceEvidenceStatus",
    "lookEvidenceStatus",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p130_implement_source_and_look_selection_separately.py"
    spec = importlib.util.spec_from_file_location("p130_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _GATE.require_text(value, label)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    displayed_source = _GATE.require_text(payload["displayedSourceId"], "displayedSourceId")
    displayed_look = _optional_text(payload["displayedLookId"], "displayedLookId")
    displayed_transfer = _GATE.require_text(payload["displayedTransfer"], "displayedTransfer")
    source_evidence = _GATE.require_text(payload["sourceEvidenceStatus"], "sourceEvidenceStatus")
    look_evidence = _GATE.require_text(payload["lookEvidenceStatus"], "lookEvidenceStatus")
    committed = bundle["committed"]
    proposed = bundle["proposed"]
    changed = bundle["info"]["changedSourceFields"]
    transfer_mismatch = not _GATE.same_transfer(displayed_transfer, committed["source_transfer"])
    evidence_promoted = source_evidence.casefold() in {"qualified", "allowed"}
    renamed = (
        displayed_source != committed["source_id"]
        or transfer_mismatch
        or bool(changed)
        or _GATE.is_imax_70mm(proposed["recording_mode"])
        or evidence_promoted
        or "imax" in source_evidence.casefold()
    )
    if renamed:
        faults.append(NEGATIVE_TOKEN)
    if displayed_look != proposed["look_id"]:
        faults.append(LOOK_HIDDEN)
    if (
        _GATE.claims_large_format(proposed["look_id"], proposed["look_params"])
        and look_evidence != "simulated"
    ):
        faults.append(_GATE.LARGE_FORMAT_UNLABELLED)
    if look_evidence.casefold() in {"qualified", "allowed"}:
        faults.append(LOOK_EVIDENCE_QUALIFIED)
    extra = [{
        "displayedSourceId": displayed_source,
        "displayedLookId": displayed_look,
        "displayedTransfer": displayed_transfer,
        "sourceEvidenceStatus": source_evidence,
        "lookEvidenceStatus": look_evidence,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        LOOK_HIDDEN: "the simulated look must be displayed independently of the source",
        LOOK_EVIDENCE_QUALIFIED: "look evidence must not be marked qualified or allowed",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
