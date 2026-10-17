"""TC-P153-02 Incomplete public source.

Host reference. A public kernel or firmware package that omits proprietary
imaging components stays incomplete. Inspectable surfaces are named, and the
omitted components remain unknown. Calling the archive a complete camera
firmware implementation without evidence is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ARCHIVE_COMPLETE = "source-archive-called-complete-without-evidence"
OMITTED_UNKNOWN = "omitted-components-remain-unknown"
INSPECTED_MISSING = "inspected-surface-not-described"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
    "archive_label",
    "inspected",
    "omitted_components",
    "claimed_complete",
    "completeness_evidence",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p153_identify_the_actual_blocked_capability.py"
    spec = importlib.util.spec_from_file_location("p153_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()
CASE = dict(_GATE.CASES[1])


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    label = _GATE.require_text(payload["archive_label"], "archive_label")
    inspected = _GATE.require_str_list(payload["inspected"], "inspected", allow_empty=True)
    omitted = _GATE.require_str_list(payload["omitted_components"], "omitted_components", allow_empty=True)
    claimed = _GATE.require_bool(payload["claimed_complete"], "claimed_complete")
    evidence = _GATE.require_optional_text(payload["completeness_evidence"], "completeness_evidence")
    overlap = sorted(set(inspected) & set(omitted))
    _GATE.require(not overlap, "a component cannot be both inspected and omitted: " + ", ".join(overlap))
    faults = list(bundle["faults"])
    if not inspected:
        faults.append(INSPECTED_MISSING)
    if claimed and omitted:
        faults.append(OMITTED_UNKNOWN)
        faults.append(ARCHIVE_COMPLETE)
    elif claimed and evidence is None:
        faults.append(ARCHIVE_COMPLETE)
    extra = [{
        "archive_label": label,
        "inspected": inspected,
        "unknownComponents": omitted,
        "claimed_complete": claimed,
        "completeness_evidence": evidence,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            ARCHIVE_COMPLETE: CASE["negative"],
            OMITTED_UNKNOWN: CASE["expected"],
            INSPECTED_MISSING: CASE["expected"],
        },
    )


def example_payload(**overrides):
    payload = _GATE.core_payload(repeat="device-variant")
    payload.update({
        "archive_label": "public-kernel",
        "inspected": ["public-kernel"],
        "omitted_components": ["proprietary-imaging-hal", "isp-firmware"],
        "claimed_complete": False,
        "completeness_evidence": None,
    })
    payload.update(overrides)
    return payload
