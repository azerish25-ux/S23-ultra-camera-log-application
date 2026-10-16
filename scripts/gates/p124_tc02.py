"""TC-P124-02 Mutable recipe during export.

Host fixture. Output frames stay bound to the frozen recipe. A live slider
change opens a new version and must not feed successive frames of the running job.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-02"
NAME = "Mutable recipe during export"
INTERVENTION = "Change UI parameters after a render has begun but before it finishes."
EXPECTED = "Keep the running job bound to its frozen recipe and create a new version for subsequent edits."
NEGATIVE = "Reading live slider values for successive output frames must fail."
REPEAT = "Repeat stock, focus, grain seed, output range, and source interpretation changes."
LIVE_SLIDER = "live-slider-frame"
RECIPE_CHANGE = "mid-job-recipe-change"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "jobId",
    "frozenRecipeSha256",
    "liveRecipeSha256",
    "frameRecipes",
    "newVersionId",
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
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    job_id = payload["jobId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if not isinstance(job_id, str) or not job_id.strip() or job_id != job_id.strip():
        raise ValueError("jobId must be a non-empty string")
    frozen = _CORE._hash(payload["frozenRecipeSha256"], "frozenRecipeSha256")
    live = _CORE._hash(payload["liveRecipeSha256"], "liveRecipeSha256")
    frames = payload["frameRecipes"]
    if not isinstance(frames, list) or not frames:
        raise ValueError("frameRecipes must be a non-empty list")
    parsed = [_CORE._hash(item, f"frameRecipes[{index}]") for index, item in enumerate(frames)]
    new_version = payload["newVersionId"]
    if new_version is not None and (
        not isinstance(new_version, str) or not new_version.strip() or new_version != new_version.strip()
    ):
        raise ValueError("newVersionId must be null or a non-empty string")

    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, NEGATIVE]
    rejected: list[str] = []
    for index, recipe in enumerate(parsed):
        if recipe != frozen:
            if recipe == live and live != frozen:
                rejected.append(LIVE_SLIDER)
                reasons.append(f"frame {index} read the live slider recipe")
            else:
                rejected.append(LIVE_SLIDER)
                reasons.append(f"frame {index} left the frozen recipe")
    if _CORE.mid_job_recipe_change(frozen, parsed + [live], job_id, new_version):
        rejected.append(RECIPE_CHANGE)
        reasons.append("live recipe changed without a new version id")
    elif live != frozen:
        reasons.append(f"subsequent edits use new version {new_version}")
        reasons.append("running frames stay on the frozen recipe")
    else:
        reasons.append("live recipe still matches the frozen recipe")
    if not rejected:
        reasons.append("running job remained bound to " + frozen)
    decision = "rejected" if rejected else "recorded"
    unique: list[str] = []
    for item in rejected:
        if item not in unique:
            unique.append(item)
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": unique,
        "preservedResults": [evidence, "jobId=" + job_id, "frozenRecipeSha256=" + frozen],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
