"""TC-P112-08 Whole-clip acceptance.

Host fixture. A full playback sequence is scored with the P112 gate. A
favorable mean boundary severity cannot hide a severe frame, and a still
sharpness number cannot qualify the clip. This is not an applyNegative stub.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P112-08"
PHASE = "P112"
WORKSTREAM = 14
NAME = "Whole-clip acceptance"
INTERVENTION = "Evaluate complete difficult clips at normal playback rather than selected best frames."
EXPECTED = "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable."
NEGATIVE = "A favorable mean score must not hide a small number of severe boundary failures."
REPEAT = "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes."
OPEN_QUESTION = "physical S23 measurement was not run"
SEVERE_TOKEN = "severe-boundary-failure-not-averaged-into-a-pass"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "claim",
    "playback_fps",
    "frames",
    "flicker_limit",
    "edge_crawl_limit",
    "severity_limit",
    "still_as_playback",
    "still_sharpness",
    "measured_on_device",
    "claims_physical_lens_qualification",
    "applyMutant",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _phase():
    path = Path(__file__).resolve().parent / "p112_qualify_temporal_lens_quality_at_normal_playback.py"
    spec = importlib.util.spec_from_file_location("p112_qualify_temporal_lens_quality_at_normal_playback", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PHASE = _phase()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(),
             label + " must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    """Run the playback gate on one whole clip and keep the case identity."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    claim = _text(payload["claim"], "claim")
    document = {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": _PHASE.BASE_REVISION,
        "evidenceId": evidence,
        "claim": claim,
        "playback_fps": payload["playback_fps"],
        "frames": payload["frames"],
        "flicker_limit": payload["flicker_limit"],
        "edge_crawl_limit": payload["edge_crawl_limit"],
        "severity_limit": payload["severity_limit"],
        "still_as_playback": payload["still_as_playback"],
        "still_sharpness": payload["still_sharpness"],
        "measured_on_device": payload["measured_on_device"],
        "claims_physical_lens_qualification": payload["claims_physical_lens_qualification"],
        "applyMutant": payload["applyMutant"],
    }
    gated = _PHASE.assess(document)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(gated["reasons"])
    if SEVERE_TOKEN in gated["rejectedClaims"]:
        reasons.append(NEGATIVE)
    result = {
        "caseId": CASE_ID,
        "decision": gated["decision"],
        "reasons": reasons,
        "rejectedClaims": list(gated["rejectedClaims"]),
        "preservedResults": list(gated["preservedResults"]),
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(result["decision"] not in {"qualified", "allowed"}, "playback must not be qualified or allowed")
    _require(evidence in result["preservedResults"], "evidence wiped")
    _require(any(item.startswith("focus_distance_variance=") for item in result["preservedResults"]),
             "focus distance variance hidden")
    _require(OPEN_QUESTION in result["openQuestions"], "physical measurement question missing")
    return result
