"""TC-P122-05 Temporary storage exhaustion.

Host fixture. Remaining space must cover intermediate work and a publication
duplicate, not only the final output bytes. Exhaustion pauses or fails without
losing the source. Recipe version bytes stay intact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P122-05"
NAME = "Temporary storage exhaustion"
INTERVENTION = "Make remaining space insufficient for intermediate work or duplicate publication storage."
EXPECTED = "Pause or fail safely before source loss, preserving recoverable artifacts and clear cleanup choices."
NEGATIVE = "Budgeting only final output bytes must fail."
REPEAT = "Repeat before rendering, during chunk assembly, and during gallery publication."
NEGATIVE_TOKEN = "budget-only-final-output-bytes"
SHORTFALL_TOKEN = "proceeded-without-intermediate-budget"
SOURCE_LOST = "source-lost"
ACTIONS = {"pause", "fail", "proceed"}
PHASE_POINTS = {"before-rendering", "chunk-assembly", "gallery-publication"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "remainingBytes",
    "intermediateBytes",
    "publicationDuplicateBytes",
    "finalOutputBytes",
    "sourcePreserved",
    "action",
    "phasePoint",
    "versions",
    "mutatedInPlace",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p122_create_non_destructive_recipe_versions",
    Path(__file__).resolve().parent / "p122_create_non_destructive_recipe_versions.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def valid_versions():
    return _CORE.sample_versions()


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bytes(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    remaining = _bytes(payload["remainingBytes"], "remainingBytes")
    intermediate = _bytes(payload["intermediateBytes"], "intermediateBytes")
    duplicate = _bytes(payload["publicationDuplicateBytes"], "publicationDuplicateBytes")
    final_output = _bytes(payload["finalOutputBytes"], "finalOutputBytes")
    if type(payload["sourcePreserved"]) is not bool:
        raise ValueError("sourcePreserved must be a bool")
    action = _text(payload["action"], "action")
    phase_point = _text(payload["phasePoint"], "phasePoint")
    if action not in ACTIONS:
        raise ValueError("action must be pause, fail, or proceed")
    if phase_point not in PHASE_POINTS:
        raise ValueError("phasePoint is not a known storage boundary")
    required = intermediate + duplicate
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    rejected = list(chain["rejectedClaims"])
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"phasePoint={phase_point}",
        f"requiredBytes={required}",
        f"finalOutputBytes={final_output}",
        f"remainingBytes={remaining}",
    ]
    reasons.extend(chain["reasons"])
    if not payload["sourcePreserved"] and SOURCE_LOST not in rejected:
        rejected.append(SOURCE_LOST)
        reasons.append("source was not preserved")
    if action == "proceed" and remaining < required:
        only_final = remaining >= final_output
        token = NEGATIVE_TOKEN if only_final else SHORTFALL_TOKEN
        if token not in rejected:
            rejected.append(token)
        if only_final:
            reasons.append(NEGATIVE)
        else:
            reasons.append("proceeded without room for intermediate and publication bytes")
    elif action == "proceed":
        reasons.append("remaining space covers intermediate work and publication storage")
    else:
        reasons.append(action + " before source loss")
    preserved = [evidence, f"requiredBytes={required}", f"phasePoint={phase_point}"]
    preserved.extend(chain["preservedResults"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
