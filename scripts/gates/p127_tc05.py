"""TC-P127-05 Temporary storage exhaustion.

Host fixture. Intermediate bytes plus duplicate publication bytes are the
budget. Final output size alone is not. Exhaustion pauses or fails without
losing the source, and leaves a cleanup choice. Bundle rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P127-05"
NAME = "Temporary storage exhaustion"
INTERVENTION = "Make remaining space insufficient for intermediate work or duplicate publication storage."
EXPECTED = "Pause or fail safely before source loss, preserving recoverable artifacts and clear cleanup choices."
NEGATIVE = "Budgeting only final output bytes must fail."
REPEAT = "Repeat before rendering, during chunk assembly, and during gallery publication."
NEGATIVE_TOKEN = "budgeted-only-final-output-bytes"
CONTINUE_TOKEN = "continued-under-storage-exhaustion"
SOURCE_TOKEN = "source-not-preserved"
CLEANUP_TOKEN = "cleanup-choice-missing"
ACTIONS = frozenset({"continue", "pause", "fail"})
SCOPES = frozenset({"final-only", "intermediate-and-publication"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "labels",
    "manifest",
    "export_allowed",
    "grade_applied",
    "metadataTexts",
    "interpretation",
    "selfDescribing",
    "publishPrivatePaths",
    "personalIdentifiers",
    "remainingBytes",
    "intermediateBytes",
    "duplicatePublicationBytes",
    "finalOutputBytes",
    "budgetScope",
    "action",
    "sourcePreserved",
    "recoverableArtifacts",
    "cleanupChoices",
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
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parent / "p127_export_interoperable_result_bundles.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _bytes(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative int")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    remaining = _bytes(payload["remainingBytes"], "remainingBytes")
    intermediate = _bytes(payload["intermediateBytes"], "intermediateBytes")
    duplicate = _bytes(payload["duplicatePublicationBytes"], "duplicatePublicationBytes")
    final_output = _bytes(payload["finalOutputBytes"], "finalOutputBytes")
    if payload["budgetScope"] not in SCOPES:
        raise ValueError("budgetScope is invalid")
    if payload["action"] not in ACTIONS:
        raise ValueError("action must be continue, pause, or fail")
    if type(payload["sourcePreserved"]) is not bool or type(payload["recoverableArtifacts"]) is not bool:
        raise ValueError("storage flags must be bools")
    choices = payload["cleanupChoices"]
    if not isinstance(choices, list) or any(not isinstance(item, str) or not item.strip() for item in choices):
        raise ValueError("cleanupChoices must be a list of non-empty strings")
    bundle = _CORE.judge_bundle(payload)
    required = intermediate + duplicate
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(bundle["reasons"])
    reasons.append(
        f"requiredBytes={required} finalOutputBytes={final_output} remainingBytes={remaining}"
    )
    rejected = list(bundle["rejectedClaims"])
    if payload["budgetScope"] == "final-only":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        if remaining >= final_output and remaining < required:
            reasons.append("final-only budget would accept work that does not fit")
    if remaining < required:
        if payload["action"] == "continue":
            rejected.append(CONTINUE_TOKEN)
            reasons.append("export continued without space for intermediates and publication")
        if not payload["sourcePreserved"]:
            rejected.append(SOURCE_TOKEN)
            reasons.append("source was not preserved")
        if not payload["recoverableArtifacts"] or not choices:
            rejected.append(CLEANUP_TOKEN)
            reasons.append("recoverable artifacts and cleanup choices are required")
        elif payload["action"] in {"pause", "fail"} and payload["sourcePreserved"]:
            reasons.append("paused or failed safely with cleanup choices: " + ",".join(choices))
    elif not payload["sourcePreserved"]:
        rejected.append(SOURCE_TOKEN)
        reasons.append("source was not preserved")
    elif payload["action"] == "continue" and payload["budgetScope"] != "final-only":
        reasons.append("remaining space covers intermediates and duplicate publication")
    preserved = [evidence, f"requiredBytes={required}"]
    preserved.extend(bundle["preservedResults"])
    result = _CORE.seal(
        CASE_ID,
        evidence,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    return result
