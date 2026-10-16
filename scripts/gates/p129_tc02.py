"""TC-P129-02 Source-look label confusion.

Host fixture. The actual source and the simulated look stay independent.
Renaming the source mode after the virtual format is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P129-02"
NAME = "Source-look label confusion"
INTERVENTION = (
    "Select a large-format film recipe while the underlying source remains a "
    "lower-resolution SDR or experimental RAW route."
)
EXPECTED = "Display the actual source and simulated look independently with their evidence status."
NEGATIVE = "Renaming a source mode after the virtual format must fail."
REPEAT = "Repeat preset changes, saved recipe reopening, and export sharing."
NEGATIVE_TOKEN = "source-renamed-after-virtual-format"
EVIDENCE_STATUS = frozenset({"measured", "provisional", "experimental", "simulated", "unverified"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceMode",
    "displayedSource",
    "sourceEvidence",
    "lookName",
    "lookEvidence",
    "capture",
    "monitoring",
    "processing",
    "warnings",
    "record_in_scroll_only",
    "warnings_visible",
)

_SPEC = importlib.util.spec_from_file_location(
    "p129_define_the_camera_screen_information_hierarchy",
    Path(__file__).resolve().parent / "p129_define_the_camera_screen_information_hierarchy.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _status(value: object, label: str) -> str:
    text = _text(value, label)
    if text not in EVIDENCE_STATUS:
        raise ValueError(f"{label} evidence status is unsupported")
    return text


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    source_mode = _text(payload["sourceMode"], "sourceMode")
    displayed = _text(payload["displayedSource"], "displayedSource")
    source_evidence = _status(payload["sourceEvidence"], "sourceEvidence")
    look_name = _text(payload["lookName"], "lookName")
    look_evidence = _status(payload["lookEvidence"], "lookEvidence")
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
    )
    rejected = list(judged["rejectedClaims"])
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"source={source_mode}:{source_evidence}",
        f"displayedSource={displayed}",
        f"look={look_name}:{look_evidence}",
    ]
    reasons.extend(judged["reasons"])
    renamed = displayed != source_mode or displayed == look_name or source_mode == look_name
    if renamed:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    else:
        reasons.append("actual source and simulated look stay independent")
    decision = "rejected" if rejected else "recorded"
    preserved = [
        evidence,
        f"source={source_mode}:{source_evidence}",
        f"look={look_name}:{look_evidence}",
        f"displayedSource={displayed}",
    ]
    preserved.extend(judged["preservedResults"])
    questions = [_CORE.PHYSICAL_NOTE, REPEAT]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)
