"""TC-P159-02 Incomplete public source.

Host reference. A public kernel or firmware-related package that omits
proprietary imaging components is not a complete camera firmware
implementation. Inspected parts stay listed; missing parts stay unknown.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P159-02",
    "phase": "P159",
    "workstream": 20,
    "name": "Incomplete public source",
    "intervention": "Provide a public kernel or firmware-related package that omits proprietary imaging components.",
    "expected": "Describe exactly what can be inspected and keep missing components unknown.",
    "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
    "repeat": "Repeat different device variants and software versions.",
}

NEGATIVE_TOKEN = "archive-called-complete-firmware"
MISSING_UNKNOWN = "missing-components-not-kept-unknown"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
    "archiveId",
    "inspectedComponents",
    "missingComponents",
    "claimedCompleteFirmware",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p159_explore_higher_quality_computational_optics.py"
    spec = importlib.util.spec_from_file_location("p159_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_components(value: object, label: str, allow_empty: bool) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    if not allow_empty:
        _GATE.require(bool(value), label + " must be non-empty")
    components = [_GATE.require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _GATE.require(len(components) == len(set(components)), label + " entries must be unique")
    return components


def _source_faults(inspected: list[str], missing: list[str], claimed_complete: bool) -> list[str]:
    faults: list[str] = []
    proprietary = _GATE.PROPRIETARY_COMPONENT
    if proprietary not in inspected and proprietary not in missing:
        faults.append(MISSING_UNKNOWN)
    if claimed_complete and (bool(missing) or proprietary not in inspected):
        faults.append(NEGATIVE_TOKEN)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    archive_id = _GATE.require_text(payload["archiveId"], "archiveId")
    inspected = _parse_components(payload["inspectedComponents"], "inspectedComponents", False)
    missing = _parse_components(payload["missingComponents"], "missingComponents", True)
    claimed = _GATE.require_bool(payload["claimedCompleteFirmware"], "claimedCompleteFirmware")
    faults = list(bundle["faults"])
    faults.extend(_source_faults(inspected, missing, claimed))
    extra = [{
        "archiveId": archive_id,
        "inspectedComponents": inspected,
        "missingComponents": missing,
        "claimedCompleteFirmware": claimed,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            MISSING_UNKNOWN: CASE["expected"],
        },
    )
