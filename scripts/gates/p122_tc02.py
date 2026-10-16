"""TC-P122-02 Mutable recipe during export.

Host fixture. A running export stays on the frozen recipe version. A slider
edit allocates a new version id and a new version_sha256. Reading live slider
values for successive frames is rejected, as is in-place mutation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P122-02"
NAME = "Mutable recipe during export"
INTERVENTION = "Change UI parameters after a render has begun but before it finishes."
EXPECTED = "Keep the running job bound to its frozen recipe and create a new version for subsequent edits."
NEGATIVE = "Reading live slider values for successive output frames must fail."
REPEAT = "Repeat stock, focus, grain seed, output range, and source interpretation changes."
NEGATIVE_TOKEN = "live-slider-values-during-export"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "versions",
    "runningExportRecipeId",
    "liveParameters",
    "readLiveSliders",
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


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    if type(payload["readLiveSliders"]) is not bool:
        raise ValueError("readLiveSliders must be a bool")
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    binding = _CORE.evaluate_binding(
        chain["versions"], payload["runningExportRecipeId"], payload["liveParameters"]
    )
    rejected = list(chain["rejectedClaims"])
    for token in binding["rejectedClaims"]:
        if token not in rejected:
            rejected.append(token)
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}"]
    reasons.extend(chain["reasons"])
    reasons.extend(binding["reasons"])
    if payload["readLiveSliders"]:
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    preserved = [evidence]
    preserved.extend(chain["preservedResults"])
    preserved.extend(binding["preservedResults"])
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
