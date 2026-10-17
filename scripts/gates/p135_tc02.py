"""TC-P135-02 Source-look label confusion.

Host fixture. The displayed source hash and each side's transfer stay
independent of a simulated look. Renaming the source after a virtual format
is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P135-02",
    "phase": "P135",
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
    "comparison",
    "displayedSourceSha256",
    "displayedLeftTransfer",
    "displayedRightTransfer",
    "sourceEvidenceStatus",
    "lookEvidenceStatus",
    "virtualFormatRenamedSource",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p135_build_side_by_side_comparison_tools.py"
    spec = importlib.util.spec_from_file_location("p135_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    displayed_source = _GATE.require_text(payload["displayedSourceSha256"], "displayedSourceSha256")
    displayed_left = _GATE.require_text(payload["displayedLeftTransfer"], "displayedLeftTransfer")
    displayed_right = _GATE.require_text(payload["displayedRightTransfer"], "displayedRightTransfer")
    source_evidence = _GATE.require_text(payload["sourceEvidenceStatus"], "sourceEvidenceStatus")
    look_evidence = _GATE.require_text(payload["lookEvidenceStatus"], "lookEvidenceStatus")
    renamed_flag = _GATE.require_bool(payload["virtualFormatRenamedSource"], "virtualFormatRenamedSource")
    left = bundle["comparison"]["left"]
    right = bundle["comparison"]["right"]
    info = bundle["info"]
    source_matches = _GATE.same_sha(displayed_source, left["source_sha256"])
    left_matches = info["transfersDeclared"] and _GATE.same_transfer(displayed_left, left["transfer"])
    right_matches = info["transfersDeclared"] and _GATE.same_transfer(displayed_right, right["transfer"])
    evidence_promoted = source_evidence.casefold() in {"qualified", "allowed"}
    renamed = (
        renamed_flag
        or not source_matches
        or not left_matches
        or not right_matches
        or source_evidence != "source"
        or evidence_promoted
    )
    if renamed:
        faults.append(NEGATIVE_TOKEN)
    if info["transfersDiffer"] and look_evidence != "simulated":
        faults.append(LOOK_HIDDEN)
    if look_evidence.casefold() in {"qualified", "allowed"}:
        faults.append(LOOK_EVIDENCE_QUALIFIED)
    extra = [{
        "displayedSourceSha256": displayed_source,
        "displayedLeftTransfer": displayed_left,
        "displayedRightTransfer": displayed_right,
        "sourceEvidenceStatus": source_evidence,
        "lookEvidenceStatus": look_evidence,
        "virtualFormatRenamedSource": renamed_flag,
        "sourceMatches": source_matches,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        LOOK_HIDDEN: "the simulated look must be displayed independently of the source",
        LOOK_EVIDENCE_QUALIFIED: "look evidence must not be marked qualified or allowed",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
