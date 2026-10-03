#!/usr/bin/env python3
"""P076 Model channel interaction conservatively.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P076-01 through TC-P076-08 modules.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
PHASE = "P076"
GOAL = "Add color response beyond independent tone curves while preserving explicit assumptions."
METHOD = "Define whether channel coupling acts on exposure, density, or reconstructed transmission. Fit or tune with held-out references, constrain instability, and separate creative saturation from material response. Document that RGB input cannot uniquely recover the original spectrum."
FIXTURE = "Neutral exposures and strongly saturated lights that stress cross-channel response."
ORACLE = "Neutral behaviour remains controlled, saturated inputs stay finite, and unsupported spectral fidelity is not claimed."
MUTANT = "Apply an arbitrary color matrix after every stage and call the result spectral simulation."
DELIVERABLE = "Channel-coupling model and stability tests"

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
