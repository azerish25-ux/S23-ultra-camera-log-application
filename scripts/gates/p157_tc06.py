"""TC-P157-06 Computational capture overclaim.

Host reference. A merge of several exposures is computational acquisition.
Motion artifacts and retained information are measured separately. Source
sample ids stay in the provenance. An attractive merge cannot erase them.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P157-06",
    "phase": "P157",
    "workstream": 20,
    "name": "Computational capture overclaim",
    "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
    "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
    "negative": "An attractive merge cannot erase its source-sampling provenance.",
    "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
}

NEGATIVE_TOKEN = "merge-erased-source-sampling-provenance"
UNLABELLED_TOKEN = "computational-acquisition-unlabelled"
MEASUREMENT_TOKEN = "computational-measurements-not-separate"
CHECK_TOKEN = "merge-artifact-checks-incomplete"
EXPOSURE_KEYS = {"id", "source"}
CHECK_KEYS = ("movingSubjects", "clippedChannels", "alignmentFailures", "temporalGhosts")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "protocolKind",
    "deviceExperimentCompleted",
    "baselinePreserved",
    "checksum",
    "logId",
    "failureTriggers",
    "thermalSafeguardDisabled",
    "capabilityMetadataFalsified",
    "experiments",
    "exposures",
    "merged",
    "presentedAsSingleUnchangedExposure",
    "labelledComputational",
    "motionArtifactsMeasured",
    "retainedInformationMeasured",
    "provenanceIds",
    "artifactChecks",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p157_design_instrumented_low_level_experiments.py"
    spec = importlib.util.spec_from_file_location("p157_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_exposures(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "exposures must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"exposures[{index}] must be an object")
        _GATE.require(set(item) == EXPOSURE_KEYS, f"exposures[{index}] keys are invalid")
        rows.append({
            "id": _GATE.require_text(item["id"], f"exposures[{index}].id"),
            "source": _GATE.require_bool(item["source"], f"exposures[{index}].source"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "exposure ids must be unique")
    return rows


def _parse_ids(value: object) -> list[str]:
    _GATE.require(isinstance(value, list), "provenanceIds must be a list")
    return [_GATE.require_text(item, f"provenanceIds[{index}]") for index, item in enumerate(value)]


def _parse_checks(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "artifactChecks must be an object")
    _GATE.require(set(value) == set(CHECK_KEYS), "artifactChecks keys are invalid")
    return {key: _GATE.require_bool(value[key], "artifactChecks." + key) for key in CHECK_KEYS}


def _merge_faults(exposures: list[dict], provenance: list[str], observed: dict, checks: dict) -> list[str]:
    if not observed["merged"]:
        return []
    source_ids = [row["id"] for row in exposures if row["source"]]
    _GATE.require(len(source_ids) >= 2, "a merge requires at least two source exposures")
    faults: list[str] = []
    if observed["presentedAsSingleUnchangedExposure"] or any(source_id not in provenance for source_id in source_ids):
        faults.append(NEGATIVE_TOKEN)
    if not observed["labelledComputational"]:
        faults.append(UNLABELLED_TOKEN)
    if not observed["motionArtifactsMeasured"] or not observed["retainedInformationMeasured"]:
        faults.append(MEASUREMENT_TOKEN)
    if not all(checks.values()):
        faults.append(CHECK_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    exposures = _parse_exposures(payload["exposures"])
    provenance = _parse_ids(payload["provenanceIds"])
    checks = _parse_checks(payload["artifactChecks"])
    observed = {
        "merged": _GATE.require_bool(payload["merged"], "merged"),
        "presentedAsSingleUnchangedExposure": _GATE.require_bool(
            payload["presentedAsSingleUnchangedExposure"],
            "presentedAsSingleUnchangedExposure",
        ),
        "labelledComputational": _GATE.require_bool(payload["labelledComputational"], "labelledComputational"),
        "motionArtifactsMeasured": _GATE.require_bool(payload["motionArtifactsMeasured"], "motionArtifactsMeasured"),
        "retainedInformationMeasured": _GATE.require_bool(
            payload["retainedInformationMeasured"],
            "retainedInformationMeasured",
        ),
    }
    faults = list(bundle["faults"])
    faults.extend(_merge_faults(exposures, provenance, observed, checks))
    observed["provenanceIds"] = provenance
    observed["sourceIds"] = [row["id"] for row in exposures if row["source"]]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [observed],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNLABELLED_TOKEN: CASE["expected"],
            MEASUREMENT_TOKEN: CASE["expected"],
            CHECK_TOKEN: CASE["repeat"],
        },
    )
