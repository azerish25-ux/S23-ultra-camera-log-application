"""TC-P160-05 Advertised unlock without delivery.

Host reference. Changing capability metadata or expanding a mode menu without
valid new sensor output fails the acquisition hypothesis. A newly visible
setting is not proof of useful capture.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P160-05",
    "phase": "P160",
    "workstream": 20,
    "name": "Advertised unlock without delivery",
    "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
    "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
    "negative": "A newly visible setting is not proof of useful capture.",
    "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
}

NEGATIVE_TOKEN = "visible-setting-proves-useful-capture"
HYPOTHESIS_NOT_FAILED = "acquisition-hypothesis-not-failed"
HYPOTHESES = frozenset({"failed", "accepted", "open"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
    "metadataChanged",
    "modeMenuExpanded",
    "validNewSensorOutput",
    "acquisitionHypothesis",
    "claimsUsefulCapture",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p160_close_the_programme_with_a_reproducible_evidence_archive.py"
    spec = importlib.util.spec_from_file_location("p160_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _unlock_faults(payload: dict) -> dict:
    metadata_changed = _GATE.require_bool(payload["metadataChanged"], "metadataChanged")
    expanded = _GATE.require_bool(payload["modeMenuExpanded"], "modeMenuExpanded")
    sensor_output = _GATE.require_bool(payload["validNewSensorOutput"], "validNewSensorOutput")
    hypothesis = _GATE.require_text(payload["acquisitionHypothesis"], "acquisitionHypothesis")
    _GATE.require(hypothesis in HYPOTHESES, "acquisitionHypothesis is not recognized")
    claims_useful = _GATE.require_bool(payload["claimsUsefulCapture"], "claimsUsefulCapture")
    advertised = metadata_changed or expanded
    faults: list[str] = []
    if advertised and not sensor_output:
        if hypothesis != "failed":
            faults.append(HYPOTHESIS_NOT_FAILED)
        if claims_useful:
            faults.append(NEGATIVE_TOKEN)
    if sensor_output and claims_useful and hypothesis == "failed":
        faults.append(HYPOTHESIS_NOT_FAILED)
    return {
        "faults": faults,
        "observed": {
            "metadataChanged": metadata_changed,
            "modeMenuExpanded": expanded,
            "validNewSensorOutput": sensor_output,
            "acquisitionHypothesis": hypothesis,
            "claimsUsefulCapture": claims_useful,
        },
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    judged = _unlock_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(judged["faults"])
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [judged["observed"]],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            HYPOTHESIS_NOT_FAILED: CASE["expected"],
        },
    )
