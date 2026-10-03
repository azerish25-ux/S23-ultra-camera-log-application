#!/usr/bin/env python3
"""P083 Scale grain by virtual gate and delivery geometry.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P083-01 through TC-P083-08 modules.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
PHASE = "P083"
GOAL = "Keep grain size meaningful when switching among small and large film formats."
METHOD = "Define grain dimensions in a declared virtual material coordinate system, then map through crop, scan, and output resampling. Test the same material profile across formats and resolutions. Do not confuse larger output resolution with a physically larger negative."
FIXTURE = "One stock rendered as Super 8, Super 16, Super 35, and fifteen-perforation large format at two delivery sizes."
ORACLE = "The apparent grain scale follows the declared gate and sampling model rather than arbitrary preset-specific pixel counts."
MUTANT = "Use a fixed two-pixel grain radius for every virtual format and output resolution."
DELIVERABLE = "Format-aware grain mapping and resolution consistency tests"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "samples",
    "claim",
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle and reject the declared mutant.

    ``samples`` are a host wedge. They must be finite. A decreasing step is a
    failed shape, not a quiet pass. ``applyMutant`` true is the mutant in the
    directive and cannot be relabelled into a measured result.
    """
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = document["evidenceId"]
    require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
            "evidenceId must be a non-empty string")
    claim = document["claim"]
    require(isinstance(claim, str) and claim.strip(), "claim must be a non-empty string")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    samples = document["samples"]
    require(isinstance(samples, list) and len(samples) >= 3, "samples must contain at least 3 numbers")
    numbers: list[float] = []
    for index, item in enumerate(samples):
        require(isinstance(item, (int, float)) and not isinstance(item, bool), f"sample {index} must be a number")
        value = float(item)
        require(math.isfinite(value), f"sample {index} must be finite")
        numbers.append(value)
    decreases = [index for index in range(1, len(numbers)) if numbers[index] < numbers[index - 1]]
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
    ]
    rejected: list[str] = []
    questions = [
        "physical S23 capture was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    if document["applyMutant"]:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
        decision = "rejected"
    elif decreases:
        rejected.append("nonmonotonic-or-reversed-response")
        reasons.append("sample wedge reversed at indexes " + ",".join(str(i) for i in decreases))
        decision = "rejected"
    else:
        reasons.append("finite monotonic host wedge retained for " + evidence)
        reasons.append("method: " + METHOD)
        decision = "recorded"
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, claim],
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    return result
